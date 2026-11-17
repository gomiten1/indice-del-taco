"""Pruebas del orquestador: orden de etapas, registro de ejecuciones y alertas por SNS."""
import json
from datetime import datetime, timezone
from io import BytesIO

import pytest

from handlers import orquestador
from tests.fakes import FakeS3
from transformacion.parquet import de_bytes

BANXICO_OK = {"fuente": "banxico", "fecha_ingesta": "2026-11-23", "series": [{"serie": "SP1", "registros": 694, "escritas": ["a"], "omitidas": ["b"]}]}
RESUMEN = lambda l, a, r, s=0: {"leidos": l, "aceptados": a, "rechazados": r, "sospechosos": s, "proporcion_cuarentena": r / l, "alerta_cuarentena": r / l > 0.1}
SILVER_OK = {"etapa": "silver", "fuentes": {"chat": RESUMEN(120, 117, 3), "banxico": RESUMEN(694, 694, 0), "receta": RESUMEN(2, 2, 0)}, "alertas": []}
GOLD_OK = {"etapa": "gold", "tablas": {"costo_taco_semanal": 117, "precio_insumo_semanal": 117, "comparativo_inflacion": 18}}


class FakeLambda:
    def __init__(self, respuestas):
        self.respuestas, self.llamadas = respuestas, []

    def invoke(self, FunctionName, Payload, **kw):
        payload = json.loads(Payload)
        self.llamadas.append((FunctionName, payload))
        cuerpo, falla = self.respuestas[FunctionName]
        if callable(cuerpo):
            cuerpo, falla = cuerpo(payload)
        r = {"Payload": BytesIO(json.dumps(cuerpo).encode())}
        if falla:
            r["FunctionError"] = "Unhandled"
        return r


class FakeSNS:
    def __init__(self):
        self.publicados = []

    def publish(self, TopicArn, Subject, Message):
        self.publicados.append((TopicArn, Subject, Message))


@pytest.fixture
def entorno(monkeypatch):
    for k, v in {"BANXICO_FUNCTION": "f-banxico", "SILVER_FUNCTION": "f-silver", "GOLD_FUNCTION": "f-gold",
                 "ALERT_TOPIC_ARN": "arn:topic", "SILVER_BUCKET": "silver"}.items():
        monkeypatch.setenv(k, v)


def correr(event=None, silver=None, banxico=None, gold=None, ahora=None):
    lam = FakeLambda({"f-banxico": (banxico or BANXICO_OK, False) if not isinstance(banxico, tuple) else banxico,
                      "f-silver": (silver or SILVER_OK, False) if not isinstance(silver, tuple) else silver,
                      "f-gold": (gold or GOLD_OK, False) if not isinstance(gold, tuple) else gold})
    sns, s3 = FakeSNS(), FakeS3()
    try:
        r = orquestador.handler(event if event is not None else {"fecha_ingesta": "2026-11-23"}, None, lambda_client=lam, sns=sns, s3=s3, ahora=ahora)
    except orquestador.OrquestadorFalla as e:
        r = e
    return r, lam, sns, s3


def registro(s3):
    [llave] = s3.llaves("silver")
    return de_bytes(s3.objetos[("silver", llave)]).to_pylist(), llave


def test_corrida_completa_invoca_en_orden_con_la_misma_fecha(entorno):
    r, lam, sns, _ = correr()
    assert [n for n, _ in lam.llamadas] == ["f-banxico", "f-silver", "f-gold"]
    assert all(p["fecha_ingesta"] == "2026-11-23" and p["ejecucion_id"] == r["ejecucion_id"] for _, p in lam.llamadas)
    assert r["estado"] == "ok" and sns.publicados == []


def test_el_registro_guarda_una_fila_por_etapa_y_fuente(entorno):
    r, _, _, s3 = correr()
    filas, llave = registro(s3)
    assert llave == f"registro_ejecuciones/{r['ejecucion_id']}.parquet"
    assert [(f["etapa"], f["fuente"], f["registros_leidos"], f["aceptados"], f["rechazados"], f["estado"]) for f in filas] == [
        ("ingesta", "banxico:SP1", 694, 694, 0, "ok"), ("silver", "chat", 120, 117, 3, "ok"), ("silver", "banxico", 694, 694, 0, "ok"),
        ("silver", "receta", 2, 2, 0, "ok"), ("gold", "gold", 0, 252, 0, "ok")]
    assert all(f["ejecucion_id"] == r["ejecucion_id"] and f["duracion_s"] is not None for f in filas)


def test_alertas_de_silver_se_publican_pero_no_detienen(entorno):
    silver = dict(SILVER_OK, alertas=["chat: cuarentena de 50% (umbral 10%)"], fuentes={**SILVER_OK["fuentes"], "chat": RESUMEN(2, 1, 1)})
    r, lam, sns, s3 = correr(silver=silver)
    assert [n for n, _ in lam.llamadas] == ["f-banxico", "f-silver", "f-gold"]  # gold sigue: lo malo ya quedó en cuarentena
    assert r["estado"] == "sospechoso" and len(sns.publicados) == 1
    topic, asunto, mensaje = sns.publicados[0]
    assert topic == "arn:topic" and asunto.isascii() and "sospechosos" in asunto.lower()
    assert "chat: cuarentena de 50%" in mensaje
    assert [f["estado"] for f in registro(s3)[0] if f["fuente"] == "chat"] == ["sospechoso"]


def test_falla_de_una_etapa_detiene_registra_avisa_y_relanza(entorno):
    err = {"errorMessage": "NoSuchKey: raw/chat/...", "errorType": "FileNotFoundError"}
    r, lam, sns, s3 = correr(silver=(err, True))
    assert isinstance(r, orquestador.OrquestadorFalla) and "silver" in str(r)
    assert [n for n, _ in lam.llamadas] == ["f-banxico", "f-silver"]  # gold no corre
    filas, _ = registro(s3)
    assert filas[-1]["etapa"] == "silver" and filas[-1]["estado"] == "error" and "NoSuchKey" in filas[-1]["detalle"]
    [(_, asunto, mensaje)] = sns.publicados
    assert asunto.isascii() and "FALLA" in asunto and "silver" in asunto
    assert "NoSuchKey" in mensaje and "/aws/lambda/" in mensaje


def test_simular_falla_se_pasa_solo_a_la_etapa_indicada(entorno):
    def silver(payload):
        return ({"errorMessage": "Falla simulada"}, True) if payload.get("simular_falla") else (SILVER_OK, False)
    r, lam, sns, _ = correr(event={"fecha_ingesta": "2026-11-23", "simular_falla": "silver"}, silver=silver)
    asignadas = {n: p.get("simular_falla") for n, p in lam.llamadas}
    assert asignadas == {"f-banxico": None, "f-silver": True}
    assert isinstance(r, orquestador.OrquestadorFalla) and "simulada" in sns.publicados[0][2].lower()


def test_sin_fecha_usa_la_de_ciudad_de_mexico(entorno):
    # 23/nov 03:00 UTC = 22/nov 21:00 en CDMX (UTC-6): la corrida del lunes 6:00 CDMX cae el 23
    r, lam, _, _ = correr(event={}, ahora=datetime(2026, 11, 23, 3, 0, tzinfo=timezone.utc))
    assert r["fecha_ingesta"] == "2026-11-22"
    r, _, _, _ = correr(event={}, ahora=datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc))
    assert r["fecha_ingesta"] == "2026-11-23"


def test_fecha_mal_formada_falla_antes_de_invocar(entorno):
    lam = FakeLambda({})
    with pytest.raises(ValueError):
        orquestador.handler({"fecha_ingesta": "23/11/2026"}, None, lambda_client=lam, sns=FakeSNS(), s3=FakeS3())
    assert lam.llamadas == []
