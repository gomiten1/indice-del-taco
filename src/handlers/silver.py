"""Lambda de silver: lee de bronze el chat, el INPC de Banxico y la receta, y escribe silver y cuarentena.

Evento opcional: {"fecha_ingesta": "AAAA-MM-DD", "ejecucion_id": "..."}; por defecto, hoy (UTC).
Variables de entorno: BRONZE_BUCKET, SILVER_BUCKET, QUARANTINE_BUCKET.
Si falta un archivo de bronze o tiene una forma inesperada, la Lambda falla (y esa falla dispara la alarma).
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone

from transformacion import silver_chat, silver_inpc, silver_receta
from transformacion.almacen import AlmacenS3
from transformacion.comun import UMBRAL_CUARENTENA


def fecha_del_evento(event: dict) -> date:
    texto = event.get("fecha_ingesta") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"fecha_ingesta debe ser AAAA-MM-DD, llegó {texto!r}") from None


def handler(event, context, s3=None) -> dict:
    event = event or {}
    fecha = fecha_del_evento(event)
    ejecucion = event.get("ejecucion_id") or getattr(context, "aws_request_id", None) or f"silver-{fecha}"
    if s3 is None:
        import boto3
        s3 = boto3.client("s3")
    bronze, silver, cuarentena = (AlmacenS3(s3, os.environ[v]) for v in ("BRONZE_BUCKET", "SILVER_BUCKET", "QUARANTINE_BUCKET"))

    chat = silver_chat.procesar_chat(bronze.get(f"raw/chat/fecha_ingesta={fecha}/chat_proveedor.txt").decode("utf-8"),
                                     "chat_proveedor.txt", fecha, ejecucion)
    silver_chat.escribir(chat, silver, cuarentena)
    inpc = silver_inpc.procesar_inpc(bronze.get(f"raw/banxico/SP1/fecha_ingesta={fecha}/SP1_datos.json"), "SP1_datos.json", fecha, ejecucion)
    silver_inpc.escribir(inpc, silver, cuarentena)
    receta = silver_receta.procesar_receta(bronze.get(f"raw/interno/fecha_ingesta={fecha}/receta.csv").decode("utf-8"),
                                           "receta.csv", fecha, ejecucion)
    silver_receta.escribir(receta, silver, cuarentena)

    fuentes = {"chat": chat.resumen, "banxico": inpc.resumen, "receta": receta.resumen}
    alertas = [f"{n}: cuarentena de {r['proporcion_cuarentena']:.0%} (umbral {UMBRAL_CUARENTENA:.0%})"
               for n, r in fuentes.items() if r["alerta_cuarentena"]]
    return {"etapa": "silver", "fecha_ingesta": str(fecha), "ejecucion_id": ejecucion, "fuentes": fuentes, "alertas": alertas}
