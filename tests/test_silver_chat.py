"""Pruebas de silver del chat: reglas de calidad, cuarentena, particiones e idempotencia."""
import hashlib
from datetime import date
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from datos_sinteticos.generador import generar_chat
from transformacion import silver_chat as sc

HOY = date(2026, 11, 16)


def msg(dia, texto, hora="6:52 a. m.", remitente="Don Beto"):
    return f"{dia}, {hora} - {remitente}: {texto}"


def procesar(*mensajes, ingesta=HOY):
    return sc.procesar_chat("\n".join(mensajes), "chat_proveedor.txt", ingesta, "ejec-1")


def filas(tabla):
    return tabla.to_pylist()


# --- contrato -----------------------------------------------------------------

def test_esquema_de_silver_coincide_con_el_diccionario():
    r = procesar(msg("15/1/26", "pastor $155 el kilo"))
    assert [(f.name, str(f.type)) for f in r.precios.schema] == [
        ("fecha_hora", "timestamp[ms]"), ("anio", "int32"), ("semana_iso", "int32"), ("producto", "string"),
        ("precio_unitario", "decimal128(10, 2)"), ("unidad", "string"), ("tipo_registro", "string"),
        ("sospechoso", "bool"), ("archivo_origen", "string"), ("linea", "int32"), ("fecha_ingesta", "date32[day]")]
    [f] = filas(r.precios)
    assert (f["producto"], f["precio_unitario"], f["unidad"], f["tipo_registro"]) == ("pastor", Decimal("155.00"), "kg", "explicito")
    assert f["fecha_ingesta"] == HOY and f["archivo_origen"] == "chat_proveedor.txt" and f["linea"] == 1


def test_esquema_de_cuarentena():
    r = procesar(msg("15/1/26", "pastor $0"))
    assert [f.name for f in r.cuarentena.schema] == [
        "fuente", "regla", "motivo", "registro_original", "archivo_origen", "linea", "ejecucion_id", "fecha_ingesta"]


def test_anio_y_semana_son_iso():
    r = procesar(msg("1/1/26", "pastor 150"), msg("29/12/25", "suadero 180"))
    por_producto = {f["producto"]: (f["anio"], f["semana_iso"]) for f in filas(r.precios)}
    assert por_producto["pastor"] == (2026, 1)
    assert por_producto["suadero"] == (2026, 1)  # lunes 29/12/2025 ya es la semana 1 de 2026 (año ISO)


# --- reglas de calidad --------------------------------------------------------

def test_rechazos_del_parser_pasan_a_cuarentena_con_su_regla():
    r = procesar(msg("15/1/26", "pastor $0"), msg("22/1/26", "suadero 185 la caja"), msg("31/2/26", "pastor 150"))
    assert r.precios.num_rows == 0
    assert [f["regla"] for f in filas(r.cuarentena)] == ["precio_invalido", "unidad_desconocida", "fecha_invalida"]
    primera = filas(r.cuarentena)[0]
    assert primera["fuente"] == "chat" and "pastor $0" in primera["registro_original"] and primera["linea"] == 1
    assert primera["ejecucion_id"] == "ejec-1" and primera["fecha_ingesta"] == HOY


def test_unidad_paquete_va_a_cuarentena():
    r = procesar(msg("15/1/26", "longaniza 90 el paquete"), msg("15/1/26", "pastor 150", hora="6:55 a. m."))
    assert [f["producto"] for f in filas(r.precios)] == ["pastor"]
    assert [f["regla"] for f in filas(r.cuarentena)] == ["unidad_no_soportada"]


def test_pieza_si_se_acepta():
    r = procesar(msg("15/1/26", "longaniza 12 la pieza"))
    assert filas(r.precios)[0]["unidad"] == "pieza" and r.cuarentena.num_rows == 0


def test_fecha_futura_va_a_cuarentena():
    r = procesar(msg("31/12/26", "pastor 150"), msg("15/1/26", "suadero 180"))
    assert [f["producto"] for f in filas(r.precios)] == ["suadero"]
    assert [f["regla"] for f in filas(r.cuarentena)] == ["fecha_futura"]


def test_variacion_extrema_se_marca_pero_no_se_descarta():
    r = procesar(msg("15/1/26", "pastor 150"), msg("22/1/26", "pastor 300"), msg("29/1/26", "pastor 305"))
    assert [(f["precio_unitario"], f["sospechoso"]) for f in filas(r.precios)] == [
        (Decimal("150.00"), False), (Decimal("300.00"), True), (Decimal("305.00"), False)]
    assert r.resumen["sospechosos"] == 1


def test_precio_repetido_y_cambio_normal_no_son_sospechosos():
    r = procesar(msg("15/1/26", "pastor 150, suadero 180"), msg("22/1/26", "pastor 155, lo demás igual"))
    assert not any(f["sospechoso"] for f in filas(r.precios))


def test_resumen_y_alerta_de_cuarentena():
    r = procesar(msg("15/1/26", "pastor 150"), msg("22/1/26", "pastor $0"))
    assert r.resumen == {"leidos": 2, "aceptados": 1, "rechazados": 1, "sospechosos": 0,
                         "proporcion_cuarentena": 0.5, "alerta_cuarentena": True}
    limpio = procesar(msg("15/1/26", "pastor 150"))
    assert limpio.resumen["alerta_cuarentena"] is False and limpio.resumen["proporcion_cuarentena"] == 0.0


def test_chat_vacio_no_truena():
    r = procesar("")
    assert r.precios.num_rows == 0 and r.cuarentena.num_rows == 0 and r.resumen["proporcion_cuarentena"] == 0.0


# --- escritura y reproceso ----------------------------------------------------

def archivos(raiz):
    return sorted(str(p.relative_to(raiz)) for p in raiz.rglob("*.parquet"))


def test_escribe_parquet_particionado_sin_columnas_de_particion(tmp_path):
    r = procesar(msg("15/1/26", "pastor 150"), msg("22/1/26", "pastor 155"))
    sc.escribir_local(r, tmp_path)
    assert archivos(tmp_path) == [
        "cuarentena/fuente=chat/fecha_ingesta=2026-11-16/chat_proveedor.parquet",
        "silver/silver_precio_proveedor/anio=2026/semana_iso=03/datos.parquet",
        "silver/silver_precio_proveedor/anio=2026/semana_iso=04/datos.parquet"]
    t = pq.read_table(tmp_path / "silver/silver_precio_proveedor/anio=2026/semana_iso=03/datos.parquet")
    assert "anio" not in t.column_names and "semana_iso" not in t.column_names  # van en la ruta (Glue/Athena)
    assert t.num_rows == 1


def test_reprocesar_es_idempotente(tmp_path):
    r = procesar(msg("15/1/26", "pastor 150"), msg("22/1/26", "pastor 155"), msg("29/1/26", "pastor $0"))
    sc.escribir_local(r, tmp_path)
    primero = {a: hashlib.sha256((tmp_path / a).read_bytes()).hexdigest() for a in archivos(tmp_path)}
    sc.escribir_local(r, tmp_path)
    segundo = {a: hashlib.sha256((tmp_path / a).read_bytes()).hexdigest() for a in archivos(tmp_path)}
    assert primero == segundo


def test_reprocesar_reemplaza_y_quita_particiones_obsoletas(tmp_path):
    sc.escribir_local(procesar(msg("15/1/26", "pastor 150"), msg("22/1/26", "pastor 155")), tmp_path)
    sc.escribir_local(procesar(msg("15/1/26", "pastor 150")), tmp_path)  # el chat nuevo ya no trae la semana 4
    assert [a for a in archivos(tmp_path) if "silver" in a] == ["silver/silver_precio_proveedor/anio=2026/semana_iso=03/datos.parquet"]


def test_cuarentena_vieja_no_sobrevive_a_un_reproceso_limpio(tmp_path):
    sc.escribir_local(procesar(msg("15/1/26", "pastor $0")), tmp_path)
    sc.escribir_local(procesar(msg("15/1/26", "pastor 150")), tmp_path)
    t = pq.read_table(tmp_path / "cuarentena/fuente=chat/fecha_ingesta=2026-11-16/chat_proveedor.parquet")
    assert t.num_rows == 0


# --- de punta a punta con el chat sintético -----------------------------------

def test_chat_sintetico_completo():
    r = sc.procesar_chat(generar_chat(semilla=42, errores=True), "chat_proveedor.txt", HOY, "ejec-1")
    assert r.precios.num_rows == 117
    assert sorted(f["regla"] for f in filas(r.cuarentena)) == ["fecha_invalida", "precio_invalido", "unidad_desconocida"]
    assert len({(f["anio"], f["semana_iso"]) for f in filas(r.precios)}) == 39  # un jueves por semana
    assert r.resumen["alerta_cuarentena"] is False and r.resumen["sospechosos"] == 0


def test_chat_sintetico_limpio_no_tiene_cuarentena():
    r = sc.procesar_chat(generar_chat(semilla=42, errores=False), "chat_proveedor.txt", HOY, "ejec-1")
    assert r.cuarentena.num_rows == 0 and r.precios.num_rows == 117
