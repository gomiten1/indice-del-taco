"""Pruebas de silver del INPC (Banxico) y de la receta."""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from transformacion import silver_inpc, silver_receta
from transformacion.almacen import AlmacenLocal
from transformacion.comun import EsquemaInesperado
from tests.datos import ARCHIVOS, TRES_SERIES, inpc_json
from transformacion.parquet import leer_tabla

FIXTURE = Path(__file__).parent.parent / "bronze_local/banxico/SP1/SP1_datos_2026-11-14.json"
HOY = date(2026, 11, 16)


def cuerpo(datos, serie="SP1"):
    return json.dumps({"bmx": {"series": [{"idSerie": serie, "titulo": "INPC", "datos": datos}]}}).encode()


def inpc(datos):
    return silver_inpc.procesar_inpc(cuerpo(datos), "SP1_datos.json", HOY, "ejec-1")


def test_inpc_real_de_bronze_local():
    r = silver_inpc.procesar_inpc(FIXTURE.read_bytes(), "SP1_datos.json", HOY, "ejec-1")
    assert r.inpc.num_rows == 694 and r.cuarentena.num_rows == 0
    ultima = max(r.inpc.to_pylist(), key=lambda f: f["fecha"])
    assert (ultima["serie_id"], ultima["fecha"], ultima["indice"]) == ("SP1", date(2026, 10, 1), Decimal("147.026000"))


def test_inpc_esquema_y_tipos():
    r = inpc([{"fecha": "01/10/2026", "dato": "147.026000000000"}])
    assert [(f.name, str(f.type)) for f in r.inpc.schema] == [
        ("serie_id", "string"), ("fecha", "date32[day]"), ("anio", "int32"), ("indice", "decimal128(12, 6)"), ("fecha_ingesta", "date32[day]")]
    assert r.inpc.to_pylist()[0]["anio"] == 2026


def test_inpc_datos_malos_van_a_cuarentena_sin_tumbar_el_resto():
    r = inpc([{"fecha": "01/01/2026", "dato": "146.0"}, {"fecha": "01/02/2026", "dato": "abc"},
              {"fecha": "31/02/2026", "dato": "147.0"}, {"fecha": "01/04/2026", "dato": "-3"}])
    assert r.inpc.num_rows == 1
    assert sorted(f["regla"] for f in r.cuarentena.to_pylist()) == ["dato_no_numerico", "fecha_invalida", "indice_invalido"]
    assert r.resumen["leidos"] == 4 and r.resumen["alerta_cuarentena"] is True


@pytest.mark.parametrize("malo", [b"no es json", b'{"error": "token"}', b'{"bmx": {"series": []}}',
                                  b'{"bmx": {"series": [{"idSerie": "SP1"}]}}'])
def test_inpc_con_estructura_inesperada_se_detiene(malo):
    with pytest.raises(EsquemaInesperado):
        silver_inpc.procesar_inpc(malo, "x.json", HOY, "e")


def test_inpc_se_escribe_particionado_por_anio_y_es_idempotente(tmp_path):
    r = inpc([{"fecha": "01/12/2025", "dato": "145.0"}, {"fecha": "01/01/2026", "dato": "146.0"}])
    silver, cuar = AlmacenLocal(tmp_path / "s"), AlmacenLocal(tmp_path / "c")
    silver_inpc.escribir(r, silver, cuar)
    silver_inpc.escribir(r, silver, cuar)
    assert silver.listar("silver_inpc/") == ["silver_inpc/anio=2025/datos.parquet", "silver_inpc/anio=2026/datos.parquet"]
    assert leer_tabla(silver, "silver_inpc").num_rows == 2


def test_receta_toma_los_gramos_de_las_aclaraciones():
    r = silver_receta.procesar_receta("producto,gramos_por_taco\nsuadero,55\npastor,50\n", "receta.csv", HOY, "e")
    assert [(f["tipo_taco"], f["insumo"], f["gramos_por_taco"]) for f in r.receta.to_pylist()] == [
        ("suadero", "suadero", 55), ("pastor", "pastor", 50)]
    assert r.cuarentena.num_rows == 0


def test_receta_con_gramos_invalidos_va_a_cuarentena():
    r = silver_receta.procesar_receta("producto,gramos_por_taco\npastor,50\nsuadero,0\nlimon,abc\n", "receta.csv", HOY, "e")
    assert [f["producto"] if "producto" in f else f["insumo"] for f in r.receta.to_pylist()] == ["pastor"]
    assert [f["regla"] for f in r.cuarentena.to_pylist()] == ["gramos_invalidos", "gramos_invalidos"]


def test_receta_sin_las_columnas_esperadas_se_detiene():
    with pytest.raises(EsquemaInesperado):
        silver_receta.procesar_receta("a,b\n1,2\n", "receta.csv", HOY, "e")


# --- N/E y varias series -------------------------------------------------------

def test_n_e_significa_sin_dato_y_no_es_un_error():
    """Banxico marca con N/E los meses en que la serie no existe: se omiten, no van a cuarentena ni disparan alerta."""
    r = inpc([{"fecha": "01/01/1969", "dato": "N/E"}, {"fecha": "01/02/1969", "dato": "N/E"}, {"fecha": "01/01/2026", "dato": "146.0"}])
    assert r.inpc.num_rows == 1 and r.cuarentena.num_rows == 0
    assert r.resumen["sin_dato"] == 2 and r.resumen["leidos"] == 1 and r.resumen["alerta_cuarentena"] is False


def test_serie_real_de_alimentos_tiene_538_meses_y_156_sin_dato():
    r = silver_inpc.procesar_inpc(inpc_json("SP66540"), "SP66540_datos.json", HOY, "e")
    assert (r.inpc.num_rows, r.cuarentena.num_rows, r.resumen["sin_dato"]) == (538, 0, 156)
    assert {f["serie_id"] for f in r.inpc.to_pylist()} == {"SP66540"}
    ult = max(r.inpc.to_pylist(), key=lambda f: f["fecha"])
    assert (ult["fecha"], ult["indice"]) == (date(2026, 10, 1), Decimal("168.671386"))  # coincide con el CSV del SIE


def resultados_de_tres_series():
    return [silver_inpc.procesar_inpc(inpc_json(s), f"{s}_datos.json", HOY, "e") for s in ARCHIVOS]


def test_combinar_series_junta_las_filas_y_suma_los_resumenes():
    c = silver_inpc.combinar(resultados_de_tres_series())
    assert c.inpc.num_rows == 694 + 538 + 538 and c.cuarentena.num_rows == 0
    assert {f["serie_id"] for f in c.inpc.to_pylist()} == set(ARCHIVOS)
    assert c.resumen["aceptados"] == 1770 and c.resumen["sin_dato"] == 312 and c.resumen["alerta_cuarentena"] is False


def test_las_tres_series_conviven_en_la_misma_particion_y_el_reproceso_es_idempotente(tmp_path):
    silver, cuar = AlmacenLocal(tmp_path / "s"), AlmacenLocal(tmp_path / "c")
    silver_inpc.escribir(silver_inpc.combinar(resultados_de_tres_series()), silver, cuar)
    primero = {k: silver.get(k) for k in silver.listar("silver_inpc/")}
    silver_inpc.escribir(silver_inpc.combinar(resultados_de_tres_series()), silver, cuar)
    assert {k: silver.get(k) for k in silver.listar("silver_inpc/")} == primero
    tabla = leer_tabla(silver, "silver_inpc")
    assert tabla.num_rows == 1770 and {f["serie_id"] for f in tabla.to_pylist()} == set(ARCHIVOS)


def test_combinar_sin_resultados_falla():
    with pytest.raises(ValueError):
        silver_inpc.combinar([])
