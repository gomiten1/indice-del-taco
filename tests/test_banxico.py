"""Pruebas de la ingesta de Banxico: sin red y sin AWS (clientes simulados)."""
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from ingesta import banxico

FIXTURE = Path(__file__).parent.parent / "bronze_local/banxico/SP1/SP1_datos_2026-11-14.json"
META = Path(__file__).parent.parent / "bronze_local/banxico/SP1/SP1_metadatos_2026-11-14.json"
TOKEN = "token-secreto-de-prueba"


class Respuesta:
    def __init__(self, cuerpo: bytes):
        self.cuerpo = cuerpo

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.cuerpo


class BancoFalso:
    """Simula la API: registra las peticiones y devuelve los archivos reales de bronze_local."""
    def __init__(self, datos=None):
        self.peticiones = []
        self.datos = FIXTURE.read_bytes() if datos is None else datos

    def __call__(self, req, timeout=None):
        self.peticiones.append(req)
        return Respuesta(self.datos if req.full_url.endswith("/datos") else META.read_bytes())


class S3Falso:
    def __init__(self):
        self.objetos = {}

    def put_object(self, Bucket, Key, Body, **kw):
        self.objetos[(Bucket, Key)] = Body


def test_clave_s3_lleva_fecha_ingesta():
    assert banxico.clave_s3("SP1", "2026-11-14", "datos") == "raw/banxico/SP1/fecha_ingesta=2026-11-14/SP1_datos.json"


def test_descargar_manda_el_token_en_el_header():
    abrir = BancoFalso()
    banxico.descargar(banxico.url_datos("SP1"), TOKEN, abrir=abrir)
    assert abrir.peticiones[0].get_header("Bmx-token") == TOKEN


def test_validar_cuenta_los_registros_del_fixture_real():
    assert banxico.validar_datos("SP1", FIXTURE.read_bytes()) == 694


def test_validar_rechaza_respuesta_sin_datos():
    vacio = json.dumps({"bmx": {"series": [{"idSerie": "SP1", "datos": []}]}}).encode()
    with pytest.raises(banxico.IngestaError):
        banxico.validar_datos("SP1", vacio)


def test_validar_rechaza_respuesta_de_error_y_json_roto():
    for cuerpo in (b'{"error": {"mensaje": "Token invalido"}}', b"<html>mantenimiento</html>"):
        with pytest.raises(banxico.IngestaError):
            banxico.validar_datos("SP1", cuerpo)


def test_validar_rechaza_otra_serie():
    with pytest.raises(banxico.IngestaError):
        banxico.validar_datos("SF43718", FIXTURE.read_bytes())


def test_error_http_no_filtra_el_token():
    def abrir(req, timeout=None):
        raise HTTPError(req.full_url, 400, "Bad Request", {}, None)
    with pytest.raises(banxico.IngestaError) as e:
        banxico.descargar(banxico.url_datos("SP1"), TOKEN, abrir=abrir)
    assert TOKEN not in str(e.value) and "400" in str(e.value)


def test_ingestar_guarda_datos_y_metadatos_en_bronze():
    s3, abrir = S3Falso(), BancoFalso()
    r = banxico.ingestar_serie("SP1", "2026-11-14", TOKEN, "bucket-bronze", s3, abrir)
    assert r["registros"] == 694
    assert set(k for _, k in s3.objetos) == {
        "raw/banxico/SP1/fecha_ingesta=2026-11-14/SP1_datos.json",
        "raw/banxico/SP1/fecha_ingesta=2026-11-14/SP1_metadatos.json"}
    assert s3.objetos[("bucket-bronze", r["claves"][0])] == FIXTURE.read_bytes()  # tal cual, sin transformar


def test_doble_ejecucion_no_duplica():
    s3 = S3Falso()
    for _ in range(2):
        banxico.ingestar_serie("SP1", "2026-11-14", TOKEN, "b", s3, BancoFalso())
    assert len(s3.objetos) == 2  # mismas llaves, se sobrescriben


def test_handler_usa_evento_y_entorno(monkeypatch):
    monkeypatch.setenv("BANXICO_TOKEN", TOKEN)
    monkeypatch.setenv("BRONZE_BUCKET", "bucket-bronze")
    s3 = S3Falso()
    r = banxico.handler({"fecha_ingesta": "2026-11-14"}, None, s3=s3, abrir=BancoFalso())
    assert r["fuente"] == "banxico" and r["fecha_ingesta"] == "2026-11-14"
    assert r["series"][0]["serie"] == "SP1" and r["series"][0]["registros"] == 694


def test_handler_rechaza_fecha_mal_formada(monkeypatch):
    monkeypatch.setenv("BANXICO_TOKEN", TOKEN)
    monkeypatch.setenv("BRONZE_BUCKET", "b")
    with pytest.raises(banxico.IngestaError):
        banxico.handler({"fecha_ingesta": "14/11/2026"}, None, s3=S3Falso(), abrir=BancoFalso())


def test_handler_sin_token_falla_claro(monkeypatch):
    monkeypatch.delenv("BANXICO_TOKEN", raising=False)
    monkeypatch.delenv("BANXICO_TOKEN_PARAM", raising=False)
    monkeypatch.setenv("BRONZE_BUCKET", "b")
    with pytest.raises(banxico.IngestaError):
        banxico.handler({}, None, s3=S3Falso(), abrir=BancoFalso())
