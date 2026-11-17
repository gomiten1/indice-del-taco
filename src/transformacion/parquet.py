"""Leer y escribir Parquet sobre un almacén (disco o S3), con particiones tipo Hive e idempotencia."""
from __future__ import annotations

from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pq

ARCHIVO = "datos.parquet"


def a_bytes(tabla: pa.Table) -> bytes:
    buf = BytesIO()
    pq.write_table(tabla, buf, compression="snappy", coerce_timestamps="ms")
    return buf.getvalue()


def de_bytes(datos: bytes) -> pa.Table:
    return pq.read_table(BytesIO(datos))


def escribir_particionada(almacen, tabla_dir: str, tabla: pa.Table, columnas_ruta: list[str], ruta_particion) -> list[str]:
    """Escribe `tabla` en `<tabla_dir>/<ruta>/datos.parquet`, una por partición (`ruta_particion(*valores)`).
    Las columnas de la ruta no van dentro del archivo (Glue/Athena las toman de la ruta). Reemplaza la tabla
    completa: borra las particiones que el resultado nuevo ya no trae."""
    grupos: dict[tuple, list[int]] = {}
    columnas = [tabla[c].to_pylist() for c in columnas_ruta]
    for i in range(tabla.num_rows):
        grupos.setdefault(tuple(col[i] for col in columnas), []).append(i)
    nuevas = []
    for valores, idx in sorted(grupos.items()):
        ruta = f"{tabla_dir}/{ruta_particion(*valores)}/{ARCHIVO}"
        almacen.put(ruta, a_bytes(tabla.take(idx).drop_columns(columnas_ruta)))
        nuevas.append(ruta)
    for vieja in almacen.listar(f"{tabla_dir}/"):
        if vieja.endswith(f"/{ARCHIVO}") and vieja not in nuevas:
            almacen.borrar(vieja)
    return nuevas


def escribir_simple(almacen, tabla_dir: str, tabla: pa.Table) -> str:
    ruta = f"{tabla_dir}/{ARCHIVO}"
    almacen.put(ruta, a_bytes(tabla))
    return ruta


def escribir_cuarentena(almacen, fuente: str, fecha_ingesta, archivo_origen: str, tabla: pa.Table) -> str:
    """Siempre escribe (aunque esté vacía) para que una cuarentena vieja no sobreviva a un reproceso limpio."""
    stem = archivo_origen.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    ruta = f"fuente={fuente}/fecha_ingesta={fecha_ingesta}/{stem}.parquet"
    almacen.put(ruta, a_bytes(tabla))
    return ruta


def leer_tabla(almacen, tabla_dir: str) -> pa.Table | None:
    """Lee todas las particiones de `tabla_dir` y agrega las columnas de la ruta (`anio=2026` -> anio int32)."""
    partes = []
    for ruta in almacen.listar(f"{tabla_dir}/"):
        if not ruta.endswith(f"/{ARCHIVO}"):
            continue
        t = de_bytes(almacen.get(ruta))
        for segmento in ruta[len(tabla_dir) + 1:].split("/")[:-1]:
            clave, _, valor = segmento.partition("=")
            col = pa.array([int(valor)] * t.num_rows, pa.int32()) if valor.isdigit() else pa.array([valor] * t.num_rows)
            t = t.append_column(clave, col)
        partes.append(t)
    return pa.concat_tables(partes) if partes else None
