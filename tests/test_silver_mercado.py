"""Silver de PROFECO (precios de mercado): equivalencias, unidades, calidad, duplicados y cobertura."""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest

from transformacion import silver_mercado as sm
from transformacion.almacen import AlmacenLocal
from transformacion.comun import EsquemaInesperado
from transformacion.parquet import leer_tabla

HOY = date(2026, 11, 18)
COLS = "producto,presentacion,marca,categoria,catalogo,precio,fecha_registro,cadena_comercial,giro,nombre_comercial,direccion,estado,municipio,latitud,longitud"
SUPER = "Supermercado / Tienda de Autoservicio"
PIERNA = "1 Kg. Granel. Pierna Entera Sin Hueso o Pernil"


def fila(producto, presentacion, precio, fecha="2026-07-16", giro=SUPER, estado="Ciudad de México", marca="S/M", comercio="Tienda 1", direccion="Calle 1"):
    return (f'"{producto}","{presentacion}","{marca}",cat,cat,{precio},{fecha},Cadena,"{giro}","{comercio}","{direccion}","{estado}",Mun,19.4,-99.1')


def csv(*filas, bom=True):
    return ("﻿" if bom else "") + COLS + "\n" + "\n".join(filas) + "\n"


def procesar(texto, archivo="b07_2026_q2.csv"):
    return sm.procesar_profeco(BytesIO(texto.encode("utf-8")), archivo, HOY, "ejec-1")


def filas(r):
    return r.mercado.to_pylist()


# --- equivalencias (ADR 0015): qué producto de PROFECO es cada insumo -----------

@pytest.mark.parametrize("producto,presentacion,insumo,equivalencia", [
    ("Carne Cerdo", PIERNA, "pastor", "proxy"),
    ("Carne Res", "1 Kg. Granel. Falda o para Deshebrar o Deshebrada", "suadero", "proxy"),
    ("Carne Cerdo", "1 Kg. Granel. Longaniza", "longaniza", "exacta"),
    ("Tortilla de Maíz", "1 Kg. Granel", "tortilla", "exacta"),
    ("Tortilla de Maíz", "Bolsa 1 Kg.", "tortilla", "exacta"),
    ("Cebolla", "1 Kg. Granel. Blanca Sin Rabo", "cebolla", "exacta"),
    ("Limón", "1 Kg. Granel. Agrio Sin Semilla o Persa", "limon", "exacta"),
    ("Piña", "1 Kg. Granel. Miel", "pina", "exacta"),
    ("Cilantro", "Manojo", "cilantro", "exacta"),
])
def test_equivalencias(producto, presentacion, insumo, equivalencia):
    assert sm.clasificar(producto, presentacion) == (insumo, equivalencia)


@pytest.mark.parametrize("producto,presentacion", [
    ("Tortilla de Harina de Trigo", "Bolsa 20+2 Piezas. 561 Gr."),   # no es de maíz
    ("Cebolla", "1 Kg. Granel. Morada"), ("Cebolla", "Manojo. Cambray"),  # solo la blanca por kilo
    ("Piña en Almíbar", "Lata 800 Gr. Trocitos"),                    # enlatada
    ("Carne Cerdo", "1 Kg. Granel. Chuleta o Chuleta Natural"), ("Carne Res", "1 Kg. Granel. Carne para Asar"),
    ("Bolígrafo Colores Varios", "Blister 10 Piezas. Punto Grueso"), ("Buscapina Compositum", "Caja con 20 Tabletas"),
])
def test_lo_que_no_es_un_insumo_se_ignora(producto, presentacion):
    assert sm.clasificar(producto, presentacion) is None


def test_precio_por_kilo_solo_cuando_la_presentacion_es_en_kilos():
    assert sm.precio_kg("1 Kg. Granel. Miel", Decimal("25.00")) == Decimal("25.00")
    assert sm.precio_kg("Bolsa 1 Kg.", Decimal("19.50")) == Decimal("19.50")
    assert sm.precio_kg("Manojo", Decimal("10.00")) is None  # no se puede convertir sin inventar el peso
    assert (sm.unidad("Manojo"), sm.unidad("1 Kg. Granel. Miel")) == ("manojo", "kg")


# --- lectura: CDMX, canal y columnas ---------------------------------------------

def test_solo_se_usa_la_ciudad_de_mexico_y_los_productos_que_son_insumos():
    r = procesar(csv(fila("Carne Cerdo", PIERNA, 108), fila("Carne Cerdo", PIERNA, 90, estado="Estado de México"),
                     fila("Bolígrafo Colores Varios", "Blister", 30)))
    assert [(f["insumo"], f["precio"]) for f in filas(r)] == [("pastor", Decimal("108.00"))]
    assert (r.resumen["filas_csv"], r.resumen["filas_cdmx"], r.resumen["leidos"]) == (3, 2, 1)


def test_central_de_abasto_es_mayoreo_y_lo_demas_menudeo():
    r = procesar(csv(fila("Carne Cerdo", PIERNA, 100, giro="Central de Abasto"), fila("Carne Cerdo", PIERNA, 110, comercio="Tienda 2")))
    assert sorted((f["canal"], f["precio"]) for f in filas(r)) == [("mayoreo", Decimal("100.00")), ("menudeo", Decimal("110.00"))]


def test_esquema_y_tipos_de_la_tabla_de_silver():
    r = procesar(csv(fila("Carne Cerdo", PIERNA, 108)))
    assert [(f.name, str(f.type)) for f in r.mercado.schema] == [
        ("fecha_registro", "date32[day]"), ("anio", "int32"), ("semana_iso", "int32"), ("producto_original", "string"), ("insumo", "string"),
        ("equivalencia", "string"), ("presentacion", "string"), ("marca", "string"), ("precio", "decimal128(10, 2)"),
        ("precio_kg", "decimal128(10, 2)"), ("unidad", "string"), ("canal", "string"), ("cadena_comercial", "string"), ("nombre_comercial", "string"),
        ("direccion", "string"), ("municipio", "string"), ("archivo_origen", "string"), ("fecha_ingesta", "date32[day]")]
    f = filas(r)[0]
    assert (f["anio"], f["semana_iso"], f["precio_kg"], f["archivo_origen"]) == (2026, 29, Decimal("108.00"), "b07_2026_q2.csv")


def test_el_bom_del_archivo_no_rompe_la_primera_columna():
    assert len(filas(procesar(csv(fila("Carne Cerdo", PIERNA, 108), bom=True)))) == 1
    assert len(filas(procesar(csv(fila("Carne Cerdo", PIERNA, 108), bom=False)))) == 1


def test_un_archivo_sin_las_columnas_esperadas_detiene_el_pipeline():
    with pytest.raises(EsquemaInesperado):
        procesar("a,b,c\n1,2,3\n")


# --- calidad: cuarentena ----------------------------------------------------------

@pytest.mark.parametrize("precio,fecha,regla", [(0, "2026-07-16", "precio_invalido"), (-5, "2026-07-16", "precio_invalido"),
                                                ("abc", "2026-07-16", "precio_invalido"), (108, "2026-02-31", "fecha_invalida"),
                                                (108, "", "fecha_invalida")])
def test_filas_malas_van_a_cuarentena_sin_tumbar_el_resto(precio, fecha, regla):
    r = procesar(csv(fila("Carne Cerdo", PIERNA, precio, fecha=fecha), fila("Carne Cerdo", PIERNA, 108, comercio="Tienda 2")))
    assert len(filas(r)) == 1
    assert [q["regla"] for q in r.cuarentena.to_pylist()] == [regla]
    assert r.cuarentena.to_pylist()[0]["fuente"] == "profeco"


# --- duplicados ---------------------------------------------------------------------

def test_duplicados_con_el_mismo_precio_se_colapsan_en_una_fila():
    r = procesar(csv(fila("Carne Cerdo", PIERNA, 108), fila("Carne Cerdo", PIERNA, 108), fila("Carne Cerdo", PIERNA, 108, comercio="Tienda 2")))
    assert len(filas(r)) == 2 and r.resumen["duplicados"] == 1


def test_duplicados_con_precios_distintos_toman_la_mediana():
    r = procesar(csv(fila("Tortilla de Maíz", "1 Kg. Granel", "22.9"), fila("Tortilla de Maíz", "1 Kg. Granel", "28.8"), fila("Tortilla de Maíz", "1 Kg. Granel", "22.9")))
    assert [f["precio"] for f in filas(r)] == [Decimal("22.90")] and r.resumen["duplicados"] == 2
    r = procesar(csv(fila("Tortilla de Maíz", "1 Kg. Granel", "18"), fila("Tortilla de Maíz", "1 Kg. Granel", "20")))
    assert [f["precio"] for f in filas(r)] == [Decimal("19.00")]


# --- cobertura (transparencia) ------------------------------------------------------

def test_el_resumen_registra_hasta_que_dia_llegan_los_datos_usados():
    r = procesar(csv(fila("Carne Cerdo", PIERNA, 108, fecha="2026-07-16"), fila("Carne Cerdo", PIERNA, 109, fecha="2026-07-31", comercio="Tienda 2"),
                     fila("Bolígrafo Colores Varios", "Blister", 30, fecha="2026-08-15")))  # una fila que no se usa no alarga la cobertura
    assert (r.resumen["fecha_min"], r.resumen["fecha_max"]) == ("2026-07-16", "2026-07-31")


def test_sin_filas_utiles_no_hay_cobertura_pero_tampoco_error():
    r = procesar(csv(fila("Bolígrafo Colores Varios", "Blister", 30)))
    assert r.mercado.num_rows == 0 and r.resumen["fecha_max"] is None and r.resumen["alerta_cuarentena"] is False


# --- varios archivos y escritura ----------------------------------------------------

def test_combinar_dos_archivos_y_no_duplicar_si_se_traslapan():
    a = procesar(csv(fila("Carne Cerdo", PIERNA, 108, fecha="2026-07-16"), fila("Carne Cerdo", PIERNA, 110, fecha="2026-07-17")), "b07_2026_q1.csv")
    b = procesar(csv(fila("Carne Cerdo", PIERNA, 110, fecha="2026-07-17"), fila("Carne Cerdo", PIERNA, 112, fecha="2026-07-30")), "b07_2026_q2.csv")
    c = sm.combinar([a, b])
    assert sorted(str(f["fecha_registro"]) for f in filas(c)) == ["2026-07-16", "2026-07-17", "2026-07-30"]
    assert (c.resumen["fecha_min"], c.resumen["fecha_max"]) == ("2026-07-16", "2026-07-30")


def test_escribir_particiona_por_semana_y_el_reproceso_es_idempotente(tmp_path):
    r = procesar(csv(fila("Carne Cerdo", PIERNA, 108, fecha="2026-07-16"), fila("Carne Cerdo", PIERNA, 109, fecha="2026-07-28", comercio="Tienda 2")))
    silver, cuar = AlmacenLocal(tmp_path / "s"), AlmacenLocal(tmp_path / "c")
    sm.escribir(r, silver, cuar)
    primero = {k: silver.get(k) for k in silver.listar("silver_precio_mercado/")}
    assert sorted(primero) == ["silver_precio_mercado/anio=2026/semana_iso=29/datos.parquet", "silver_precio_mercado/anio=2026/semana_iso=31/datos.parquet"]
    sm.escribir(r, silver, cuar)
    assert {k: silver.get(k) for k in silver.listar("silver_precio_mercado/")} == primero
    assert leer_tabla(silver, "silver_precio_mercado").num_rows == 2
