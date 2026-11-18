"""Pruebas de los handlers de Lambda (silver y gold) con S3 simulado."""
from pathlib import Path

import pytest

from datos_sinteticos.generador import generar_chat
from handlers import gold, silver
from tests.datos import inpc_json
from tests.fakes import FakeS3
from transformacion.almacen import AlmacenS3
from transformacion.parquet import de_bytes, leer_tabla

BANXICO = (Path(__file__).parent.parent / "bronze_local/banxico/SP1/SP1_datos_2026-11-14.json").read_bytes()
RECETA = "producto,gramos_por_taco\nsuadero,55\npastor,50\n"
FECHA = "2026-11-16"


@pytest.fixture
def entorno(monkeypatch):
    for k, v in {"BRONZE_BUCKET": "bronze", "SILVER_BUCKET": "silver", "QUARANTINE_BUCKET": "cuarentena", "GOLD_BUCKET": "gold"}.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def s3(entorno):
    f = FakeS3()
    f.put_object(Bucket="bronze", Key=f"raw/chat/fecha_ingesta={FECHA}/chat_proveedor.txt", Body=generar_chat(42, True).encode())
    f.put_object(Bucket="bronze", Key=f"raw/banxico/SP1/fecha_ingesta={FECHA}/SP1_datos.json", Body=BANXICO)
    f.put_object(Bucket="bronze", Key=f"raw/interno/fecha_ingesta={FECHA}/receta.csv", Body=RECETA.encode())
    return f


def test_silver_procesa_las_tres_fuentes_y_escribe_en_sus_buckets(s3):
    r = silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    assert r["etapa"] == "silver" and r["fecha_ingesta"] == FECHA
    assert r["fuentes"]["chat"]["aceptados"] == 117 and r["fuentes"]["banxico"]["aceptados"] == 694 and r["fuentes"]["receta"]["aceptados"] == 2
    assert len([k for k in s3.llaves("silver") if k.startswith("silver_precio_proveedor/")]) == 39
    assert "silver_receta/datos.parquet" in s3.llaves("silver") and len([k for k in s3.llaves("silver") if k.startswith("silver_inpc/")]) > 50
    assert f"fuente=chat/fecha_ingesta={FECHA}/chat_proveedor.parquet" in s3.llaves("cuarentena")
    assert r["alertas"] == []


def test_silver_es_idempotente_en_s3(s3):
    silver.handler({"fecha_ingesta": FECHA, "ejecucion_id": "x"}, None, s3=s3)
    antes = dict(s3.objetos)
    silver.handler({"fecha_ingesta": FECHA, "ejecucion_id": "x"}, None, s3=s3)
    assert s3.objetos == antes


def test_silver_avisa_si_la_cuarentena_pasa_del_umbral(s3):
    s3.put_object(Bucket="bronze", Key=f"raw/chat/fecha_ingesta={FECHA}/chat_proveedor.txt",
                  Body=b"15/1/26, 6:52 a. m. - Don Beto: pastor $0\n22/1/26, 6:52 a. m. - Don Beto: pastor 150\n")
    r = silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    assert r["alertas"] == ["chat: cuarentena de 50% (umbral 10%)"]


def test_silver_sin_el_archivo_de_bronze_falla(s3):
    s3.objetos.pop(("bronze", f"raw/banxico/SP1/fecha_ingesta={FECHA}/SP1_datos.json"))
    with pytest.raises(FileNotFoundError, match="raw/banxico"):
        silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)


def test_silver_usa_el_archivo_mas_reciente_disponible(s3):
    """El chat no se sube cada semana: la corrida del 23 usa el del 16 y deja la fecha de origen a la vista."""
    s3.put_object(Bucket="bronze", Key="raw/banxico/SP1/fecha_ingesta=2026-11-23/SP1_datos.json", Body=BANXICO)
    r = silver.handler({"fecha_ingesta": "2026-11-23"}, None, s3=s3)
    assert r["fechas_origen"] == {"chat": FECHA, "banxico": "2026-11-23", "receta": FECHA}
    assert r["alertas"] == []  # 7 dias de rezago del chat: todavia dentro de lo normal


def test_silver_avisa_si_una_fuente_esta_atrasada(s3):
    s3.put_object(Bucket="bronze", Key="raw/banxico/SP1/fecha_ingesta=2026-12-01/SP1_datos.json", Body=BANXICO)
    r = silver.handler({"fecha_ingesta": "2026-12-01"}, None, s3=s3)
    assert r["alertas"] == ["chat: datos de hace 15 dias (mas de 10)"]  # la receta casi no cambia: no cuenta


def test_silver_ignora_archivos_de_fechas_futuras(s3):
    s3.put_object(Bucket="bronze", Key="raw/chat/fecha_ingesta=2027-01-01/chat_proveedor.txt", Body=b"basura")
    assert silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)["fechas_origen"]["chat"] == FECHA


@pytest.mark.parametrize("handler", [silver.handler, gold.handler])
def test_simular_falla_lanza_el_error_de_prueba(handler, s3):
    with pytest.raises(RuntimeError, match="simulada"):
        handler({"fecha_ingesta": FECHA, "simular_falla": True}, None, s3=s3)


@pytest.mark.parametrize("handler", [silver.handler, gold.handler])
def test_fecha_mal_formada_falla(handler, s3):
    with pytest.raises(ValueError):
        handler({"fecha_ingesta": "16/11/2026"}, None, s3=s3)


def test_gold_calcula_y_escribe_las_tablas(s3):
    silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    r = gold.handler({}, None, s3=s3)
    assert r["etapa"] == "gold" and set(r["tablas"]) == {"costo_taco_semanal", "precio_insumo_semanal", "comparativo_inflacion", "contribucion_insumo", "comparativo_proveedor"}
    assert s3.llaves("gold") == ["comparativo_inflacion/datos.parquet", "comparativo_proveedor/datos.parquet", "contribucion_insumo/datos.parquet",
                                 "costo_taco_semanal/datos.parquet", "precio_insumo_semanal/datos.parquet"]
    assert r["tablas"]["costo_taco_semanal"] > 0


def test_gold_es_idempotente(s3):
    silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    gold.handler({}, None, s3=s3)
    antes = {k: v for k, v in s3.objetos.items() if k[0] == "gold"}
    gold.handler({}, None, s3=s3)
    assert {k: v for k, v in s3.objetos.items() if k[0] == "gold"} == antes


def test_gold_sin_silver_falla_claro(s3):
    with pytest.raises(ValueError, match="silver_precio_proveedor"):
        gold.handler({}, None, s3=s3)


# --- varias series de Banxico (N4: inflación de alimentos) -----------------------

def agregar_series(s3, fecha=FECHA, series=("SP66540", "SP56386")):
    for serie in series:
        s3.put_object(Bucket="bronze", Key=f"raw/banxico/{serie}/fecha_ingesta={fecha}/{serie}_datos.json", Body=inpc_json(serie))


def test_silver_combina_todas_las_series_de_banxico_en_una_tabla(s3):
    agregar_series(s3)
    r = silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    assert r["fuentes"]["banxico"]["aceptados"] == 694 + 538 + 538 and r["fuentes"]["banxico"]["sin_dato"] == 312
    assert r["alertas"] == []  # los meses N/E no cuentan como errores
    tabla = leer_tabla(AlmacenS3(s3, "silver"), "silver_inpc")
    assert {f["serie_id"] for f in tabla.to_pylist()} == {"SP1", "SP66540", "SP56386"}


def test_silver_sigue_funcionando_si_solo_hay_el_inpc_general(s3):
    r = silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    assert r["fuentes"]["banxico"]["aceptados"] == 694 and r["alertas"] == []


def test_silver_avisa_si_una_serie_de_banxico_esta_atrasada(s3):
    s3.put_object(Bucket="bronze", Key="raw/banxico/SP1/fecha_ingesta=2026-11-23/SP1_datos.json", Body=inpc_json("SP1"))
    agregar_series(s3, fecha="2026-11-01", series=("SP66540",))
    r = silver.handler({"fecha_ingesta": "2026-11-23"}, None, s3=s3)
    assert r["alertas"] == ["banxico: SP66540 con datos de hace 22 dias (mas de 10)"]
    assert r["fechas_origen"]["banxico"] == "2026-11-01"  # la más antigua de las series


def test_silver_ignora_una_serie_que_solo_tiene_archivos_futuros(s3):
    agregar_series(s3, fecha="2027-01-01", series=("SP66540",))
    r = silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    assert r["fuentes"]["banxico"]["aceptados"] == 694


def test_gold_llena_alimentos_y_pecuarios_cuando_estan_en_silver(s3):
    agregar_series(s3)
    silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    gold.handler({}, None, s3=s3)
    infl = de_bytes(s3.objetos[("gold", "comparativo_inflacion/datos.parquet")]).to_pylist()
    sep = next(f for f in infl if f["tipo_taco"] == "pastor" and f["mes"] == 9)
    assert sep["inpc_general_base100"] is not None and sep["inpc_alimentos_base100"] is not None and sep["inpc_pecuarios_base100"] is not None


# --- PROFECO (opcional, cargado a mano) ---------------------------------------------

MUESTRA_PROFECO = (Path(__file__).parent.parent / "bronze_local/profeco/csv/b07_2026_q2_muestra.csv").read_bytes()


def test_sin_csv_de_profeco_silver_y_gold_siguen_como_antes(s3):
    r = silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    assert "profeco" not in r["fuentes"] and r["cobertura_profeco"] is None
    assert not [k for k in s3.llaves("silver") if k.startswith("silver_precio_mercado/")]
    assert gold.handler({}, None, s3=s3)["tablas"]["comparativo_proveedor"] == 0


def test_con_csv_de_profeco_silver_registra_la_cobertura_y_gold_llena_p2(s3):
    s3.put_object(Bucket="bronze", Key=f"raw/profeco/fecha_ingesta={FECHA}/b07_2026_q2.csv", Body=MUESTRA_PROFECO)
    r = silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    assert r["fuentes"]["profeco"]["aceptados"] == 1839
    assert r["cobertura_profeco"] == {"desde": "2026-07-16", "hasta": "2026-07-31"}
    assert sorted({k.split("/")[2] for k in s3.llaves("silver") if k.startswith("silver_precio_mercado/")}) == ["semana_iso=29", "semana_iso=30", "semana_iso=31"]
    g = gold.handler({}, None, s3=s3)
    assert g["tablas"]["comparativo_proveedor"] == 9


def test_un_csv_de_una_fecha_posterior_no_se_usa_todavia(s3):
    s3.put_object(Bucket="bronze", Key="raw/profeco/fecha_ingesta=2026-12-01/b07_2026_q3.csv", Body=MUESTRA_PROFECO)
    assert "profeco" not in silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)["fuentes"]
