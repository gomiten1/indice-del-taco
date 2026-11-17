"""Pruebas de los handlers de Lambda (silver y gold) con S3 simulado."""
from pathlib import Path

import pytest

from datos_sinteticos.generador import generar_chat
from handlers import gold, silver
from tests.fakes import FakeS3, NoSuchKey

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
    with pytest.raises(NoSuchKey):
        silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)


@pytest.mark.parametrize("handler", [silver.handler, gold.handler])
def test_fecha_mal_formada_falla(handler, s3):
    with pytest.raises(ValueError):
        handler({"fecha_ingesta": "16/11/2026"}, None, s3=s3)


def test_gold_calcula_y_escribe_las_tablas(s3):
    silver.handler({"fecha_ingesta": FECHA}, None, s3=s3)
    r = gold.handler({}, None, s3=s3)
    assert r["etapa"] == "gold" and set(r["tablas"]) == {"costo_taco_semanal", "precio_insumo_semanal", "comparativo_inflacion"}
    assert s3.llaves("gold") == ["comparativo_inflacion/datos.parquet", "costo_taco_semanal/datos.parquet", "precio_insumo_semanal/datos.parquet"]
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
