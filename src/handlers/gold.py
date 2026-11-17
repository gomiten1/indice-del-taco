"""Lambda de gold: lee silver, calcula el costo por taco, el índice y la comparación con la inflación, y escribe gold.

Evento opcional: {"semana_base": "AAAA-MM-DD"} (un lunes) para fijar la semana base (ADR 0009).
Variables de entorno: SILVER_BUCKET, GOLD_BUCKET.
"""
from __future__ import annotations

import os
from datetime import datetime

from transformacion import gold, parquet
from transformacion.almacen import AlmacenS3


def handler(event, context, s3=None) -> dict:
    event = event or {}
    semana_base = None
    if event.get("fecha_ingesta"):  # se acepta (y valida) para poder encadenar con silver con el mismo evento
        from handlers.silver import fecha_del_evento
        fecha_del_evento(event)
    if event.get("semana_base"):
        semana_base = datetime.strptime(event["semana_base"], "%Y-%m-%d").date()
    if s3 is None:
        import boto3
        s3 = boto3.client("s3")
    silver, destino = AlmacenS3(s3, os.environ["SILVER_BUCKET"]), AlmacenS3(s3, os.environ["GOLD_BUCKET"])

    precios, receta, inpc = (parquet.leer_tabla(silver, t) for t in ("silver_precio_proveedor", "silver_receta", "silver_inpc"))
    for nombre, tabla in (("silver_precio_proveedor", precios), ("silver_receta", receta)):
        if tabla is None:
            raise ValueError(f"No hay datos en {nombre}: corre primero la Lambda de silver")
    tablas = gold.calcular_gold(precios, receta, inpc, semana_base=semana_base)
    for nombre, tabla in tablas.items():
        parquet.escribir_simple(destino, nombre, tabla)
    return {"etapa": "gold", "tablas": {n: t.num_rows for n, t in tablas.items()}}
