"""Piezas compartidas por todas las tablas de silver: cuarentena, resumen y umbral de alerta."""
from __future__ import annotations

import pyarrow as pa

UMBRAL_CUARENTENA = 0.10  # si se rechaza más de esta proporción de los registros leídos, hay alerta

ESQUEMA_CUARENTENA = pa.schema([
    ("fuente", pa.string()),
    ("regla", pa.string()),
    ("motivo", pa.string()),
    ("registro_original", pa.string()),
    ("archivo_origen", pa.string()),
    ("linea", pa.int32()),
    ("ejecucion_id", pa.string()),
    ("fecha_ingesta", pa.date32()),
])


class EsquemaInesperado(ValueError):
    """El archivo de origen no tiene la forma esperada: el pipeline se detiene y avisa (no se adivina)."""


def fila_cuarentena(fuente, regla, motivo, registro_original, archivo_origen, linea, ejecucion_id, fecha_ingesta) -> dict:
    return {"fuente": fuente, "regla": regla, "motivo": motivo, "registro_original": registro_original,
            "archivo_origen": archivo_origen, "linea": linea, "ejecucion_id": ejecucion_id, "fecha_ingesta": fecha_ingesta}


def armar_resumen(leidos: int, aceptados: int, rechazados: int, sospechosos: int = 0) -> dict:
    proporcion = rechazados / leidos if leidos else 0.0
    return {"leidos": leidos, "aceptados": aceptados, "rechazados": rechazados, "sospechosos": sospechosos,
            "proporcion_cuarentena": proporcion, "alerta_cuarentena": proporcion > UMBRAL_CUARENTENA}
