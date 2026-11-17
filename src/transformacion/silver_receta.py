"""Silver de la receta (gramos de cada insumo por taco). Contrato: docs/diccionario_datos.md (`silver_receta`).

Hoy la receta solo trae la carne (55 g de suadero, 50 g de pastor; aclaración A2). Tortilla, verduras y salsa
no tienen dato del cliente: se agregan filas cuando lleguen (ADR 0005), sin cambiar el código.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

import pyarrow as pa

from transformacion import parquet
from transformacion.comun import ESQUEMA_CUARENTENA, EsquemaInesperado, armar_resumen, fila_cuarentena

FUENTE = "receta"
TABLA_SILVER = "silver_receta"
VIGENTE_DESDE = date(2026, 1, 1)  # supuesto sintético: el cliente no dio la fecha de vigencia
ESQUEMA_RECETA = pa.schema([
    ("tipo_taco", pa.string()),
    ("insumo", pa.string()),
    ("gramos_por_taco", pa.int32()),
    ("vigente_desde", pa.date32()),
])


@dataclass(frozen=True)
class ResultadoReceta:
    receta: pa.Table
    cuarentena: pa.Table
    resumen: dict
    archivo_origen: str
    fecha_ingesta: date


def procesar_receta(texto: str, archivo_origen: str, fecha_ingesta: date, ejecucion_id: str,
                    vigente_desde: date = VIGENTE_DESDE) -> ResultadoReceta:
    lector = csv.DictReader(io.StringIO(texto))
    if not lector.fieldnames or not {"producto", "gramos_por_taco"} <= set(lector.fieldnames):
        raise EsquemaInesperado(f"{archivo_origen}: se esperaban las columnas producto y gramos_por_taco")
    filas, cuarentena, leidos = [], [], 0
    for n, f in enumerate(lector, start=2):  # la línea 1 es el encabezado
        leidos += 1
        try:
            gramos = int(f["gramos_por_taco"])
            if gramos <= 0:
                raise ValueError
        except (TypeError, ValueError):
            cuarentena.append(fila_cuarentena(FUENTE, "gramos_invalidos", f"gramos_por_taco debe ser un entero mayor a cero: {f['gramos_por_taco']!r}",
                                              ",".join(f"{v}" for v in f.values()), archivo_origen, n, ejecucion_id, fecha_ingesta))
            continue
        filas.append({"tipo_taco": f["producto"], "insumo": f["producto"], "gramos_por_taco": gramos, "vigente_desde": vigente_desde})
    return ResultadoReceta(pa.Table.from_pylist(filas, schema=ESQUEMA_RECETA), pa.Table.from_pylist(cuarentena, schema=ESQUEMA_CUARENTENA),
                           armar_resumen(leidos, len(filas), len(cuarentena)), archivo_origen, fecha_ingesta)


def escribir(resultado: ResultadoReceta, silver, cuarentena) -> list[str]:
    return [parquet.escribir_simple(silver, TABLA_SILVER, resultado.receta),
            parquet.escribir_cuarentena(cuarentena, FUENTE, resultado.fecha_ingesta, resultado.archivo_origen, resultado.cuarentena)]
