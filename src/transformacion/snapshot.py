"""Exporta el snapshot público (gold -> CSV) que lee el dashboard de Streamlit. Reemplaza la copia manual.

Qué sale y qué no (ADR 0006 y ADR 0012): se publican índices, costos por taco en pesos, brechas e inflación. Nunca salen
las columnas ni las filas con el precio de compra del proveedor (`precio_proveedor_kg`, `fuente = 'proveedor'`).
Se acepta que, con la receta pública, el costo por taco permite estimar ese precio (ADR 0012).

Uso:  PYTHONPATH=.:src python -m transformacion.snapshot --gold data/lake/gold --salida snapshot_gold
      PYTHONPATH=.:src python -m transformacion.snapshot --bucket indice-del-taco-dev-gold-<ID>   # lee gold de S3 (necesita boto3)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow as pa

from transformacion import parquet
from transformacion.almacen import AlmacenLocal, AlmacenS3

TABLAS_GOLD = ("costo_taco_semanal", "precio_insumo_semanal", "comparativo_inflacion", "contribucion_insumo", "comparativo_proveedor")
COLUMNAS_PRIVADAS = {"precio_proveedor_kg"}
# P2 todavía no existe en gold (necesita PROFECO): el CSV queda con encabezado y sin filas, que el dashboard muestra como "aún sin datos".
ENCABEZADO_SIN_DATOS = {"comparativo_proveedor": "anio,semana_iso,insumo,precio_menudeo_kg,precio_mayoreo_kg,brecha_menudeo_pct,brecha_mayoreo_pct,aproximado,diagnostico"}


def leer_gold(almacen) -> dict[str, pa.Table | None]:
    return {nombre: parquet.leer_tabla(almacen, nombre) for nombre in TABLAS_GOLD}


def _sanear(nombre: str, tabla: pa.Table) -> pa.Table:
    tabla = tabla.drop_columns([c for c in tabla.column_names if c in COLUMNAS_PRIVADAS])
    if "fuente" in tabla.column_names:
        tabla = tabla.filter(pa.compute.not_equal(tabla["fuente"], "proveedor"))
    return tabla


def exportar(gold: dict[str, pa.Table | None], salida: Path) -> list[Path]:
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    rutas = []
    for nombre in TABLAS_GOLD:
        ruta = salida / f"{nombre}.csv"
        tabla = gold.get(nombre)
        if tabla is None:
            ruta.write_text(ENCABEZADO_SIN_DATOS[nombre] + "\n", encoding="utf-8")
        else:
            _sanear(nombre, tabla).to_pandas().to_csv(ruta, index=False, lineterminator="\n")
        rutas.append(ruta)
    return rutas


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Exporta el snapshot público de gold para el dashboard.")
    ap.add_argument("--gold", type=Path, default=Path("data/lake/gold"), help="carpeta local con las tablas gold")
    ap.add_argument("--bucket", help="en lugar de --gold: bucket S3 de gold")
    ap.add_argument("--salida", type=Path, default=Path("snapshot_gold"))
    a = ap.parse_args()
    if a.bucket:
        import boto3
        origen = AlmacenS3(boto3.client("s3"), a.bucket)
    else:
        origen = AlmacenLocal(a.gold)
    for ruta in exportar(leer_gold(origen), a.salida):
        print(ruta)
