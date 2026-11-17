"""Silver del chat del proveedor: parser + reglas de calidad + Parquet particionado + cuarentena.

Contrato: docs/diccionario_datos.md (`silver_precio_proveedor` y `cuarentena`).
Es lógica pura sobre texto y tablas: no sabe de S3. `escribir_local` guarda en disco; la Lambda
de silver usará las mismas funciones (`procesar_chat`, `particiones`) y escribirá a S3.

Reglas (SOW §5, ADR 0007):
  - Precio, fecha y unidad desconocida: las valida el parser y sus rechazos pasan a cuarentena.
  - `fecha_futura` y `unidad_no_soportada` (paquete: no se puede convertir a kg): cuarentena.
  - Variación mayor a UMBRAL_VARIACION contra el precio anterior: se marca `sospechoso`, NO se descarta.
  - Si más de UMBRAL_CUARENTENA de los registros se rechazan, el resumen trae `alerta_cuarentena`.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import pyarrow as pa

from ingesta.parser_chat import parsear_chat
from transformacion import parquet
from transformacion.almacen import AlmacenLocal
from transformacion.comun import ESQUEMA_CUARENTENA, UMBRAL_CUARENTENA, armar_resumen, fila_cuarentena  # noqa: F401

UMBRAL_VARIACION = Decimal("0.25")
UNIDADES_SILVER = {"kg", "pieza"}
FUENTE = "chat"
TABLA_SILVER = "silver_precio_proveedor"

ESQUEMA_PRECIOS = pa.schema([
    ("fecha_hora", pa.timestamp("ms")),
    ("anio", pa.int32()),
    ("semana_iso", pa.int32()),
    ("producto", pa.string()),
    ("precio_unitario", pa.decimal128(10, 2)),
    ("unidad", pa.string()),
    ("tipo_registro", pa.string()),
    ("sospechoso", pa.bool_()),
    ("archivo_origen", pa.string()),
    ("linea", pa.int32()),
    ("fecha_ingesta", pa.date32()),
])
COLUMNAS_DE_RUTA = ["anio", "semana_iso"]  # van en la ruta (Glue/Athena), no dentro del archivo


@dataclass(frozen=True)
class ResultadoSilver:
    precios: pa.Table
    cuarentena: pa.Table
    resumen: dict
    archivo_origen: str
    fecha_ingesta: date


def procesar_chat(texto: str, archivo_origen: str, fecha_ingesta: date, ejecucion_id: str) -> ResultadoSilver:
    parseo = parsear_chat(texto)
    limite = datetime.combine(fecha_ingesta, time.max)

    cuarentena = [fila_cuarentena(FUENTE, r.motivo, r.detalle, r.texto, archivo_origen, r.linea, ejecucion_id, fecha_ingesta)
                  for r in parseo.rechazos]

    aceptados = []
    for p in parseo.precios:
        regla = motivo = None
        if p.fecha > limite:
            regla, motivo = "fecha_futura", f"{p.fecha:%Y-%m-%d} es posterior a la fecha de ingesta {fecha_ingesta}"
        elif p.unidad not in UNIDADES_SILVER:
            regla, motivo = "unidad_no_soportada", f"{p.producto}: la unidad '{p.unidad}' no se puede convertir a kg o pieza"
        if regla:
            cuarentena.append(fila_cuarentena(FUENTE, regla, motivo, f"{p.fecha:%Y-%m-%d %H:%M} {p.producto} {p.precio} {p.unidad}",
                                              archivo_origen, p.linea, ejecucion_id, fecha_ingesta))
        else:
            aceptados.append(p)

    anterior: dict[tuple[str, str], Decimal] = {}
    filas = []
    for p in sorted(aceptados, key=lambda x: x.fecha):  # orden cronológico para comparar contra el precio previo
        previo = anterior.get((p.producto, p.unidad))
        sospechoso = previo is not None and abs(p.precio / previo - 1) > UMBRAL_VARIACION
        anterior[(p.producto, p.unidad)] = p.precio
        iso = p.fecha.isocalendar()
        filas.append({
            "fecha_hora": p.fecha, "anio": iso.year, "semana_iso": iso.week, "producto": p.producto,
            "precio_unitario": p.precio, "unidad": p.unidad, "tipo_registro": p.tipo, "sospechoso": sospechoso,
            "archivo_origen": archivo_origen, "linea": p.linea, "fecha_ingesta": fecha_ingesta})

    leidos = len(parseo.precios) + len(parseo.rechazos)
    resumen = armar_resumen(leidos, len(filas), len(cuarentena), sum(f["sospechoso"] for f in filas))
    return ResultadoSilver(pa.Table.from_pylist(filas, schema=ESQUEMA_PRECIOS),
                           pa.Table.from_pylist(cuarentena, schema=ESQUEMA_CUARENTENA),
                           resumen, archivo_origen, fecha_ingesta)


def escribir(resultado: ResultadoSilver, silver, cuarentena) -> list[str]:
    """Escribe silver y cuarentena en los almacenes dados (disco o S3). Idempotente: el mismo chat deja los mismos
    archivos y el reproceso reemplaza (también borra las particiones que el chat nuevo ya no trae)."""
    rutas = parquet.escribir_particionada(silver, TABLA_SILVER, resultado.precios, COLUMNAS_DE_RUTA,
                                          lambda anio, semana: f"anio={anio}/semana_iso={semana:02d}")
    rutas.append(parquet.escribir_cuarentena(cuarentena, FUENTE, resultado.fecha_ingesta, resultado.archivo_origen,
                                             resultado.cuarentena))
    return rutas


def escribir_local(resultado: ResultadoSilver, raiz) -> list[str]:
    raiz = Path(raiz)
    return escribir(resultado, AlmacenLocal(raiz / "silver"), AlmacenLocal(raiz / "cuarentena"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Silver del chat del proveedor (local).")
    ap.add_argument("--entrada", type=Path, default=Path("data/sintetico/chat_proveedor.txt"))
    ap.add_argument("--salida", type=Path, default=Path("data/lake"))
    ap.add_argument("--fecha-ingesta", type=date.fromisoformat, default=date.today())
    ap.add_argument("--ejecucion-id", default=None)
    a = ap.parse_args()
    r = procesar_chat(a.entrada.read_text(encoding="utf-8"), a.entrada.name, a.fecha_ingesta,
                      a.ejecucion_id or f"local-{a.fecha_ingesta}")
    escribir_local(r, a.salida)
    print(json.dumps(r.resumen, indent=2))
