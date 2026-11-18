"""Silver del INPC (Banxico SP1): JSON de bronze -> Parquet particionado por año, con cuarentena.

Contrato: docs/diccionario_datos.md (`silver_inpc`). Banxico entrega el índice como texto y la fecha como
dd/mm/aaaa; aquí se tipan. Los meses `N/E` (sin dato) se omiten sin error. Si el JSON no tiene la forma esperada se lanza `EsquemaInesperado` (se detiene el
pipeline y se avisa); una fila mala va a cuarentena sin tumbar las demás.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pyarrow as pa

from transformacion import parquet
from transformacion.comun import ESQUEMA_CUARENTENA, EsquemaInesperado, armar_resumen, fila_cuarentena

FUENTE = "banxico"
TABLA_SILVER = "silver_inpc"
SIN_DATO = {"N/E"}  # Banxico marca así los meses en que la serie no existe (p. ej. 1969 a 1981): no es un error ni se inventa un valor
ESQUEMA_INPC = pa.schema([
    ("serie_id", pa.string()),
    ("fecha", pa.date32()),
    ("anio", pa.int32()),
    ("indice", pa.decimal128(12, 6)),
    ("fecha_ingesta", pa.date32()),
])


@dataclass(frozen=True)
class ResultadoInpc:
    inpc: pa.Table
    cuarentena: pa.Table
    resumen: dict
    archivo_origen: str
    fecha_ingesta: date


def procesar_inpc(cuerpo: bytes, archivo_origen: str, fecha_ingesta: date, ejecucion_id: str) -> ResultadoInpc:
    try:
        serie = json.loads(cuerpo)["bmx"]["series"][0]
        serie_id, datos = serie["idSerie"], serie["datos"]
        if not isinstance(datos, list):
            raise TypeError("datos no es una lista")
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise EsquemaInesperado(f"{archivo_origen}: no trae bmx.series[0].datos ({e})") from None

    filas, cuarentena, sin_dato = [], [], 0
    for n, d in enumerate(datos, start=1):
        original = json.dumps(d, ensure_ascii=False)
        if isinstance(d, dict) and str(d.get("dato", "")).strip().upper() in SIN_DATO:
            sin_dato += 1  # ADR 0019: sin dato; se omite, no va a cuarentena ni cuenta para la alerta
            continue

        def rechazar(regla, motivo):
            cuarentena.append(fila_cuarentena(FUENTE, regla, motivo, original, archivo_origen, n, ejecucion_id, fecha_ingesta))

        try:
            fecha = datetime.strptime(d["fecha"], "%d/%m/%Y").date()
        except (KeyError, ValueError, TypeError):
            rechazar("fecha_invalida", f"fecha no válida: {d.get('fecha') if isinstance(d, dict) else d!r}")
            continue
        try:
            indice = Decimal(d["dato"]).quantize(Decimal("0.000001"))
            if not indice.is_finite():
                raise InvalidOperation
        except (KeyError, InvalidOperation, TypeError):
            rechazar("dato_no_numerico", f"dato no numérico: {d.get('dato')!r}")
            continue
        if indice <= 0:
            rechazar("indice_invalido", f"el índice debe ser mayor a cero: {indice}")
            continue
        filas.append({"serie_id": serie_id, "fecha": fecha, "anio": fecha.year, "indice": indice, "fecha_ingesta": fecha_ingesta})

    resumen = armar_resumen(len(datos) - sin_dato, len(filas), len(cuarentena))
    resumen["sin_dato"] = sin_dato
    return ResultadoInpc(pa.Table.from_pylist(filas, schema=ESQUEMA_INPC),
                         pa.Table.from_pylist(cuarentena, schema=ESQUEMA_CUARENTENA), resumen, archivo_origen, fecha_ingesta)


def combinar(resultados: list[ResultadoInpc]) -> ResultadoInpc:
    """Junta varias series en un solo resultado. Hace falta porque silver REEMPLAZA la tabla completa al escribir:
    escribir cada serie por separado haría que cada una borrara a las demás."""
    if not resultados:
        raise ValueError("No hay series para combinar")
    suma = lambda clave: sum(r.resumen[clave] for r in resultados)
    resumen = armar_resumen(suma("leidos"), suma("aceptados"), suma("rechazados"))
    resumen["sin_dato"] = suma("sin_dato")
    return ResultadoInpc(pa.concat_tables([r.inpc for r in resultados]), pa.concat_tables([r.cuarentena for r in resultados]),
                         resumen, "series_banxico", max(r.fecha_ingesta for r in resultados))


def escribir(resultado: ResultadoInpc, silver, cuarentena) -> list[str]:
    rutas = parquet.escribir_particionada(silver, TABLA_SILVER, resultado.inpc, ["anio"], lambda anio: f"anio={anio}")
    rutas.append(parquet.escribir_cuarentena(cuarentena, FUENTE, resultado.fecha_ingesta, resultado.archivo_origen, resultado.cuarentena))
    return rutas
