"""Pruebas de gold: costo por taco e índice (P1), precio por insumo y comparación con inflación (P4).

Escenario con cifras calculadas a mano (receta: pastor 50 g, suadero 55 g):
  pastor   $150 el 1/ene (sem 1), $155 el 15/ene (sem 3), $160 el 12/feb (sem 7)
  suadero  $180 el 1/ene (sem 1)
  INPC     ene 146.0, feb 147.46
"""
from datetime import date, datetime
from decimal import Decimal

import pyarrow as pa
import pytest

from transformacion import gold
from transformacion.silver_chat import ESQUEMA_PRECIOS
from transformacion.silver_inpc import ESQUEMA_INPC
from transformacion.silver_receta import ESQUEMA_RECETA

D = Decimal


def precios(*eventos):
    filas = []
    for fecha, producto, precio, *resto in eventos:
        iso = fecha.isocalendar()
        filas.append({"fecha_hora": fecha, "anio": iso.year, "semana_iso": iso.week, "producto": producto,
                      "precio_unitario": D(precio), "unidad": resto[0] if resto else "kg", "tipo_registro": "explicito",
                      "sospechoso": False, "archivo_origen": "chat.txt", "linea": 1, "fecha_ingesta": date(2026, 11, 16)})
    return pa.Table.from_pylist(filas, schema=ESQUEMA_PRECIOS)


def receta(*lineas):
    return pa.Table.from_pylist([{"tipo_taco": t, "insumo": i, "gramos_por_taco": g, "vigente_desde": date(2026, 1, 1)}
                                 for t, i, g in lineas], schema=ESQUEMA_RECETA)


def inpc(*meses, serie="SP1"):
    return pa.Table.from_pylist([{"serie_id": serie, "fecha": f, "anio": f.year, "indice": D(v), "fecha_ingesta": date(2026, 11, 16)}
                                 for f, v in meses], schema=ESQUEMA_INPC)


def varias(*tablas):
    return pa.concat_tables(tablas)


PRECIOS = precios(
    (datetime(2026, 1, 1, 7, 0), "pastor", "150"), (datetime(2026, 1, 1, 7, 0), "suadero", "180"),
    (datetime(2026, 1, 15, 7, 0), "pastor", "155"), (datetime(2026, 2, 12, 7, 0), "pastor", "160"))
RECETA = receta(("pastor", "pastor", 50), ("suadero", "suadero", 55))
INPC = inpc((date(2026, 1, 1), "146.0"), (date(2026, 2, 1), "147.46"))


def calcular(**kw):
    return gold.calcular_gold(kw.pop("precios", PRECIOS), kw.pop("receta", RECETA), kw.pop("inpc", INPC), **kw)


def filas(tabla):
    return tabla.to_pylist()


def costo(g, tipo, merma=False):
    return [f for f in filas(g["costo_taco_semanal"]) if f["tipo_taco"] == tipo and f["incluye_merma"] == merma]


# --- P1: costo por taco e índice ---------------------------------------------

def test_costo_semanal_carga_el_precio_vigente_hasta_que_cambia():
    pastor = costo(calcular(), "pastor")
    assert [(f["semana_iso"], f["costo_taco_mxn"]) for f in pastor] == [
        (1, D("7.50")), (2, D("7.50")), (3, D("7.75")), (4, D("7.75")), (5, D("7.75")), (6, D("7.75")), (7, D("8.00"))]
    assert pastor[0]["semana_inicio"] == date(2025, 12, 29) and pastor[0]["anio"] == 2026  # año ISO


def test_indice_base_100_en_la_primera_semana_completa():
    pastor = costo(calcular(), "pastor")
    assert [f["indice_base100"] for f in pastor] == [D("100.00"), D("100.00"), D("103.33"), D("103.33"), D("103.33"), D("103.33"), D("106.67")]
    assert {f["semana_base"] for f in pastor} == {date(2025, 12, 29)}
    suadero = costo(calcular(), "suadero")
    assert {f["costo_taco_mxn"] for f in suadero} == {D("9.90")} and {f["indice_base100"] for f in suadero} == {D("100.00")}


def test_esquema_de_costo_taco_semanal():
    t = calcular()["costo_taco_semanal"]
    assert [(f.name, str(f.type)) for f in t.schema] == [
        ("anio", "int32"), ("semana_iso", "int32"), ("semana_inicio", "date32[day]"), ("tipo_taco", "string"),
        ("costo_taco_mxn", "decimal128(8, 2)"), ("indice_base100", "decimal128(8, 2)"), ("semana_base", "date32[day]"),
        ("incluye_merma", "bool"), ("insumos_con_dato", "int32")]


def test_merma_solo_aplica_al_pastor():
    g = calcular()
    assert [f["costo_taco_mxn"] for f in costo(g, "pastor", merma=True)][:3] == [D("8.52"), D("8.52"), D("8.81")]  # 7.5/0.88 y 7.75/0.88
    assert costo(g, "suadero", merma=True) == []
    chico = calcular(merma_pastor=D("0.0"))
    assert costo(chico, "pastor", merma=True)[0]["costo_taco_mxn"] == D("7.50")


def test_semana_base_configurable():
    pastor = costo(calcular(semana_base=date(2026, 1, 12)), "pastor")
    assert [f["indice_base100"] for f in pastor][:4] == [None, None, D("100.00"), D("100.00")]
    assert pastor[6]["indice_base100"] == D("103.23")  # 8.00 / 7.75


def test_insumo_de_la_receta_sin_precio_no_inventa_indice():
    """ADR 0005/0009: el costo cuenta solo los insumos con dato y el índice espera a que estén todos."""
    g = calcular(receta=receta(("pastor", "pastor", 50), ("pastor", "tortilla", 30)))
    pastor = costo(g, "pastor")
    assert pastor[0]["costo_taco_mxn"] == D("7.50") and pastor[0]["insumos_con_dato"] == 1
    assert all(f["indice_base100"] is None and f["semana_base"] is None for f in pastor)


def test_precios_en_pieza_no_cuentan_para_el_costo():
    p = precios((datetime(2026, 1, 1, 7, 0), "pastor", "150", "pieza"))
    assert filas(calcular(precios=p)["costo_taco_semanal"]) == []


# --- precio por insumo --------------------------------------------------------

def test_precio_insumo_semanal_del_proveedor():
    t = calcular()["precio_insumo_semanal"]
    pastor = [f for f in filas(t) if f["insumo"] == "pastor"]
    assert [(f["semana_iso"], f["precio"], f["n_observaciones"]) for f in pastor][:3] == [
        (1, D("150.00"), 1), (2, D("150.00"), 0), (3, D("155.00"), 1)]
    assert {(f["fuente"], f["estadistico"]) for f in pastor} == {("proveedor", "ultimo_vigente")}


# --- P4: inflación -------------------------------------------------------------

def test_comparativo_inflacion_mensual_con_misma_base():
    por_tipo = {(f["tipo_taco"], f["mes"]): f for f in filas(calcular()["comparativo_inflacion"])}
    ene, feb = por_tipo[("pastor", 1)], por_tipo[("pastor", 2)]
    assert (ene["indice_taco_base100"], ene["inpc_general_base100"], ene["brecha_pp"]) == (D("100.00"), D("100.00"), D("0.00"))
    # índice medio: enero (100+100+103.33x3)/5 = 102.0; febrero (103.33+106.67)/2 = 105.0 -> 105/102 = 102.94
    assert (feb["indice_taco_base100"], feb["inpc_general_base100"], feb["brecha_pp"]) == (D("102.94"), D("101.00"), D("1.94"))
    assert feb["base_mes"] == date(2026, 1, 1) and feb["inpc_alimentos_base100"] is None
    assert por_tipo[("suadero", 2)]["brecha_pp"] == D("-1.00")


def test_mes_sin_inpc_deja_la_comparacion_vacia_pero_conserva_el_indice():
    g = calcular(inpc=inpc((date(2026, 1, 1), "146.0")))
    feb = [f for f in filas(g["comparativo_inflacion"]) if f["tipo_taco"] == "pastor" and f["mes"] == 2][0]
    assert feb["indice_taco_base100"] == D("102.94") and feb["inpc_general_base100"] is None and feb["brecha_pp"] is None


# --- bordes -------------------------------------------------------------------

def test_sin_datos_devuelve_tablas_vacias():
    g = gold.calcular_gold(precios(), RECETA, None)
    assert all(t.num_rows == 0 for t in g.values())
    assert set(g) == {"costo_taco_semanal", "precio_insumo_semanal", "comparativo_inflacion", "contribucion_insumo", "comparativo_proveedor"}


def test_calculo_determinista():
    assert calcular() == calcular()


# --- P3: contribución de cada insumo al cambio de costo ------------------------

def contribucion(g, tipo, trimestre="2026Q1"):
    return [f for f in filas(g["contribucion_insumo"]) if f["tipo_taco"] == tipo and f["trimestre"] == trimestre]


def test_esquema_de_contribucion_insumo():
    t = calcular()["contribucion_insumo"]
    assert [(f.name, str(f.type)) for f in t.schema] == [
        ("trimestre", "string"), ("tipo_taco", "string"), ("insumo", "string"), ("aportacion_mxn", "decimal128(8, 2)"),
        ("aportacion_pct", "decimal128(8, 2)"), ("ranking", "int32"), ("estado", "string")]


def test_la_carne_explica_el_aumento_y_los_demas_insumos_salen_sin_dato():
    """Pastor: de $150 a $160 en el trimestre = +$0.50 por taco (50 g). El resto de la lista del taco no tiene dato."""
    pastor = contribucion(calcular(), "pastor")
    assert [(f["insumo"], f["aportacion_mxn"], f["aportacion_pct"], f["ranking"], f["estado"]) for f in pastor] == [
        ("pastor", D("0.50"), D("100.00"), 1, "ok"),
        ("tortilla", None, None, 2, "sin dato"), ("cebolla", None, None, 3, "sin dato"), ("cilantro", None, None, 4, "sin dato"),
        ("limon", None, None, 5, "sin dato"), ("pina", None, None, 6, "sin dato")]


def test_sin_cambio_de_precio_no_inventa_porcentajes():
    suadero = contribucion(calcular(), "suadero")
    assert (suadero[0]["insumo"], suadero[0]["aportacion_mxn"], suadero[0]["aportacion_pct"], suadero[0]["estado"]) == ("suadero", D("0.00"), None, "sin cambio")


def test_los_porcentajes_de_los_insumos_con_dato_suman_100():
    p = precios((datetime(2026, 1, 1, 7, 0), "pastor", "150"), (datetime(2026, 2, 12, 7, 0), "pastor", "160"),
                (datetime(2026, 1, 1, 7, 0), "tortilla", "20"), (datetime(2026, 2, 12, 7, 0), "tortilla", "22"))
    g = calcular(precios=p, receta=receta(("pastor", "pastor", 50), ("pastor", "tortilla", 30)))
    pastor = contribucion(g, "pastor")
    assert [(f["insumo"], f["aportacion_mxn"], f["aportacion_pct"], f["ranking"]) for f in pastor[:2]] == [
        ("pastor", D("0.50"), D("89.29"), 1), ("tortilla", D("0.06"), D("10.71"), 2)]  # 0.50/0.56 y 0.06/0.56
    assert [f["estado"] for f in pastor[2:]] == ["sin dato"] * 4 and [f["ranking"] for f in pastor[2:]] == [3, 4, 5, 6]


def test_un_trimestre_con_una_sola_semana_no_se_reporta():
    p = precios((datetime(2026, 1, 1, 7, 0), "pastor", "150"))
    assert filas(calcular(precios=p)["contribucion_insumo"]) == []


# --- N4: inflación de alimentos y de pecuarios ---------------------------------

def test_esquema_de_comparativo_inflacion_con_alimentos_y_pecuarios():
    t = calcular()["comparativo_inflacion"]
    assert [(f.name, str(f.type)) for f in t.schema] == [
        ("anio", "int32"), ("mes", "int32"), ("tipo_taco", "string"), ("indice_taco_base100", "decimal128(8, 2)"),
        ("inpc_general_base100", "decimal128(8, 2)"), ("inpc_alimentos_base100", "decimal128(8, 2)"),
        ("inpc_pecuarios_base100", "decimal128(8, 2)"), ("base_mes", "date32[day]"), ("brecha_pp", "decimal128(8, 2)")]


def test_alimentos_y_pecuarios_usan_la_misma_base_que_el_indice_del_taco():
    """Mes base = enero. Alimentos 200 -> 206 (103.00); pecuarios 100 -> 95 (95.00); el INPC general sigue en 101.00."""
    todo = varias(INPC, inpc((date(2026, 1, 1), "200.0"), (date(2026, 2, 1), "206.0"), serie="SP66540"),
                  inpc((date(2026, 1, 1), "100.0"), (date(2026, 2, 1), "95.0"), serie="SP56386"))
    por_mes = {(f["tipo_taco"], f["mes"]): f for f in filas(calcular(inpc=todo)["comparativo_inflacion"])}
    ene, feb = por_mes[("pastor", 1)], por_mes[("pastor", 2)]
    assert (ene["inpc_alimentos_base100"], ene["inpc_pecuarios_base100"]) == (D("100.00"), D("100.00"))
    assert (feb["inpc_alimentos_base100"], feb["inpc_pecuarios_base100"], feb["inpc_general_base100"]) == (D("103.00"), D("95.00"), D("101.00"))
    assert feb["brecha_pp"] == D("1.94")  # la brecha sigue medida contra el INPC general


def test_sin_las_series_de_alimentos_quedan_vacias_pero_el_resto_se_calcula():
    feb = [f for f in filas(calcular()["comparativo_inflacion"]) if f["tipo_taco"] == "pastor" and f["mes"] == 2][0]
    assert feb["inpc_alimentos_base100"] is None and feb["inpc_pecuarios_base100"] is None
    assert feb["inpc_general_base100"] == D("101.00") and feb["indice_taco_base100"] == D("102.94")


def test_una_serie_de_alimentos_sin_el_mes_base_queda_vacia():
    todo = varias(INPC, inpc((date(2026, 2, 1), "206.0"), serie="SP66540"))  # falta enero (el mes base)
    feb = [f for f in filas(calcular(inpc=todo)["comparativo_inflacion"]) if f["tipo_taco"] == "pastor" and f["mes"] == 2][0]
    assert feb["inpc_alimentos_base100"] is None


# --- P2: proveedor contra el mercado (PROFECO) --------------------------------------

def _mercado(*filas):
    """filas: (insumo, año, semana, canal, precio, unidad, equivalencia)."""
    from transformacion.silver_mercado import ESQUEMA_MERCADO
    base = {"fecha_registro": date(2026, 1, 5), "producto_original": "x", "presentacion": "p", "marca": "", "cadena_comercial": "",
            "nombre_comercial": "", "direccion": "", "municipio": "", "archivo_origen": "a.csv", "fecha_ingesta": date(2026, 11, 18)}
    return pa.Table.from_pylist([{**base, "insumo": i, "anio": a, "semana_iso": s, "canal": c, "precio": D(p), "precio_kg": D(p) if u == "kg" else None,
                                  "unidad": u, "equivalencia": e} for i, a, s, c, p, u, e in filas], schema=ESQUEMA_MERCADO)


def test_el_mercado_semanal_es_la_mediana_por_canal_y_unidad():
    m = _mercado(("pastor", 2026, 1, "menudeo", "100", "kg", "proxy"), ("pastor", 2026, 1, "menudeo", "110", "kg", "proxy"),
                 ("pastor", 2026, 1, "menudeo", "130", "kg", "proxy"), ("cilantro", 2026, 1, "menudeo", "10", "manojo", "exacta"))
    t = {(f["insumo"], f["fuente"]): f for f in filas(calcular(mercado=m)["precio_insumo_semanal"]) if f["fuente"] != "proveedor"}
    assert (t[("pastor", "menudeo")]["precio"], t[("pastor", "menudeo")]["n_observaciones"], t[("pastor", "menudeo")]["unidad"]) == (D("110.00"), 3, "kg")
    assert (t[("cilantro", "menudeo")]["precio"], t[("cilantro", "menudeo")]["unidad"], t[("cilantro", "menudeo")]["estadistico"]) == (D("10.00"), "manojo", "mediana")


def test_p2_brecha_diagnostico_y_aproximado():
    p = [f for f in filas(calcular(mercado=_mercado(("pastor", 2026, 1, "menudeo", "100", "kg", "proxy"),
                                                    ("pastor", 2026, 1, "mayoreo", "120", "kg", "proxy")))["comparativo_proveedor"])]
    assert len(p) == 1 and p[0]["insumo"] == "pastor" and p[0]["precio_proveedor_kg"] == D("150.00")
    assert (p[0]["brecha_menudeo_pct"], p[0]["brecha_mayoreo_pct"], p[0]["aproximado"], p[0]["diagnostico"]) == (D("50.00"), D("25.00"), True, "caro")


@pytest.mark.parametrize("precio_mercado,diagnostico", [("100", "caro"), ("136.36", "en rango"), ("150", "en rango"), ("165", "en rango"), ("200", "barato")])
def test_p2_umbral_del_diagnostico(precio_mercado, diagnostico):
    f = filas(calcular(mercado=_mercado(("pastor", 2026, 1, "menudeo", precio_mercado, "kg", "exacta")))["comparativo_proveedor"])[0]
    assert f["diagnostico"] == diagnostico and f["aproximado"] is False


def test_p2_sin_mercado_en_esa_semana_no_hay_fila_y_un_manojo_no_se_compara_con_un_kilo():
    assert calcular()["comparativo_proveedor"].num_rows == 0
    m = _mercado(("pastor", 2026, 1, "menudeo", "100", "manojo", "exacta"), ("pastor", 2026, 40, "menudeo", "100", "kg", "exacta"))
    assert calcular(mercado=m)["comparativo_proveedor"].num_rows == 0
