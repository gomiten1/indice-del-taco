"""Orquestador semanal: Banxico -> silver -> gold, con registro de ejecuciones y alertas por correo (SNS).

Lo dispara EventBridge Scheduler (lunes 6:00, hora de CDMX). Evento opcional:
  {"fecha_ingesta": "AAAA-MM-DD", "simular_falla": "silver"}   # etapa: ingesta, silver o gold
Si una etapa falla: se registra, se avisa por SNS y se detiene (lo malo no se usa). Si silver reporta datos
sospechosos o atrasados: se avisa pero se sigue (lo malo ya quedó en cuarentena). El registro de cada corrida queda
en `registro_ejecuciones/<ejecucion_id>.parquet` del bucket silver (contrato en docs/diccionario_datos.md).

Variables de entorno: BANXICO_FUNCTION, SILVER_FUNCTION, GOLD_FUNCTION, ALERT_TOPIC_ARN, SILVER_BUCKET.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timezone
from decimal import Decimal

import pyarrow as pa

from handlers.comun import hoy_cdmx
from handlers.silver import fecha_del_evento
from transformacion import parquet

ESQUEMA_REGISTRO = pa.schema([
    ("ejecucion_id", pa.string()), ("fecha_hora_inicio", pa.timestamp("ms")), ("fecha_ingesta", pa.date32()),
    ("etapa", pa.string()), ("fuente", pa.string()), ("registros_leidos", pa.int32()), ("aceptados", pa.int32()),
    ("rechazados", pa.int32()), ("duracion_s", pa.decimal128(8, 2)), ("estado", pa.string()), ("detalle", pa.string())])


class OrquestadorFalla(RuntimeError):
    """Una etapa falló: la corrida se detuvo y ya se avisó por correo."""


def _invocar(lam, funcion: str, payload: dict) -> tuple[dict, bool]:
    r = lam.invoke(FunctionName=funcion, Payload=json.dumps(payload).encode(), InvocationType="RequestResponse")
    return json.loads(r["Payload"].read()), bool(r.get("FunctionError"))


def _filas_de(etapa: str, cuerpo: dict, alertas: list[str]) -> list[dict]:
    if etapa == "ingesta":
        return [{"fuente": f"banxico:{s['serie']}", "leidos": s["registros"], "aceptados": s["registros"], "rechazados": 0,
                 "estado": "ok", "detalle": f"escritas={len(s['escritas'])} omitidas={len(s['omitidas'])}"} for s in cuerpo["series"]]
    if etapa == "silver":
        return [{"fuente": n, "leidos": r["leidos"], "aceptados": r["aceptados"], "rechazados": r["rechazados"],
                 "estado": "sospechoso" if any(a.startswith(f"{n}:") for a in alertas) or r["sospechosos"] else "ok",
                 "detalle": json.dumps({"fecha_origen": cuerpo.get("fechas_origen", {}).get(n), "sospechosos": r["sospechosos"]})}
                for n, r in cuerpo["fuentes"].items()]
    return [{"fuente": "gold", "leidos": 0, "aceptados": sum(cuerpo["tablas"].values()), "rechazados": 0, "estado": "ok",
             "detalle": json.dumps(cuerpo["tablas"])}]


def handler(event, context, lambda_client=None, sns=None, s3=None, ahora: datetime | None = None) -> dict:
    event = event or {}
    ahora = ahora or datetime.now(timezone.utc)
    fecha = fecha_del_evento({"fecha_ingesta": event.get("fecha_ingesta") or str(hoy_cdmx(ahora))})
    ejecucion = getattr(context, "aws_request_id", None) or f"ejec-{ahora:%Y%m%d%H%M%S}"
    if lambda_client is None or sns is None or s3 is None:
        import boto3
        lambda_client, sns, s3 = lambda_client or boto3.client("lambda"), sns or boto3.client("sns"), s3 or boto3.client("s3")
    topico, bucket = os.environ["ALERT_TOPIC_ARN"], os.environ["SILVER_BUCKET"]
    etapas = [("ingesta", os.environ["BANXICO_FUNCTION"]), ("silver", os.environ["SILVER_FUNCTION"]), ("gold", os.environ["GOLD_FUNCTION"])]

    filas, alertas, falla = [], [], None
    for etapa, funcion in etapas:
        payload = {"fecha_ingesta": str(fecha), "ejecucion_id": ejecucion}
        if event.get("simular_falla") == etapa:
            payload["simular_falla"] = True
        t0 = time.monotonic()
        cuerpo, con_error = _invocar(lambda_client, funcion, payload)
        duracion = Decimal(str(round(time.monotonic() - t0, 2)))
        if con_error:
            detalle = f"{cuerpo.get('errorType', 'Error')}: {cuerpo.get('errorMessage', '')}"
            filas.append({"fuente": "-", "leidos": 0, "aceptados": 0, "rechazados": 0, "estado": "error", "detalle": detalle[:1000],
                          "etapa": etapa, "duracion_s": duracion})
            falla = (etapa, funcion, detalle)
            break
        if etapa == "silver":
            alertas = cuerpo.get("alertas", [])
        for f in _filas_de(etapa, cuerpo, alertas):
            filas.append({**f, "etapa": etapa, "duracion_s": duracion})

    registro = pa.Table.from_pylist([{
        "ejecucion_id": ejecucion, "fecha_hora_inicio": ahora.replace(tzinfo=None), "fecha_ingesta": fecha, "etapa": f["etapa"],
        "fuente": f["fuente"], "registros_leidos": f["leidos"], "aceptados": f["aceptados"], "rechazados": f["rechazados"],
        "duracion_s": f["duracion_s"], "estado": f["estado"], "detalle": f["detalle"]} for f in filas], schema=ESQUEMA_REGISTRO)
    s3.put_object(Bucket=bucket, Key=f"registro_ejecuciones/{ejecucion}.parquet", Body=parquet.a_bytes(registro))

    if falla:
        etapa, funcion, detalle = falla
        sns.publish(TopicArn=topico, Subject=f"[Indice del Taco] FALLA en {etapa}", Message=(
            f"La corrida semanal del Indice del Taco se detuvo en la etapa '{etapa}'.\n\n"
            f"Fecha de ingesta: {fecha}\nEjecucion: {ejecucion}\nError: {detalle}\n\n"
            f"Los datos de gold NO se actualizaron; el dashboard sigue mostrando la corrida anterior.\n"
            f"Revisa los logs en CloudWatch: /aws/lambda/{funcion}\n"
            + ("\n(Esta falla es una SIMULACION a proposito para probar las alertas.)\n" if "simulada" in detalle.lower() else "")))
        raise OrquestadorFalla(f"Fallo la etapa {etapa}: {detalle}")
    if alertas:
        sns.publish(TopicArn=topico, Subject="[Indice del Taco] Datos sospechosos o atrasados", Message=(
            f"La corrida del {fecha} termino, pero hay datos que revisar:\n\n" + "\n".join(f"- {a}" for a in alertas)
            + f"\n\nEjecucion: {ejecucion}. Los registros con errores quedaron en cuarentena y no se usaron."))
    return {"etapa": "orquestador", "fecha_ingesta": str(fecha), "ejecucion_id": ejecucion,
            "estado": "sospechoso" if alertas else "ok", "alertas": alertas, "filas_registradas": len(filas)}
