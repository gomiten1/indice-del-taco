"""Corre el pipeline completo (silver + gold) en local sobre archivos de disco; sirve para reproducir el snapshot
sin AWS, para probar cambios y para el CI. Los mismos módulos corren en las Lambdas.

Uso:  PYTHONPATH=.:src python -m transformacion.pipeline_local            # genera datos sintéticos si faltan
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from transformacion import gold, parquet, silver_chat, silver_inpc, silver_receta
from transformacion.almacen import AlmacenLocal


def correr(chat: Path, receta: Path, inpc, fecha_ingesta: date, salida: Path, ejecucion_id: str = "local") -> dict:
    """`inpc`: un archivo JSON de Banxico o una lista de ellos (una serie por archivo; SP1 es la obligatoria)."""
    salida = Path(salida)
    inpc = [Path(inpc)] if isinstance(inpc, (str, Path)) else [Path(x) for x in inpc]
    silver, cuarentena, destino = (AlmacenLocal(salida / d) for d in ("silver", "cuarentena", "gold"))
    c = silver_chat.procesar_chat(Path(chat).read_text(encoding="utf-8"), Path(chat).name, fecha_ingesta, ejecucion_id)
    silver_chat.escribir(c, silver, cuarentena)
    i = silver_inpc.combinar([silver_inpc.procesar_inpc(x.read_bytes(), x.name, fecha_ingesta, ejecucion_id) for x in inpc])
    silver_inpc.escribir(i, silver, cuarentena)
    r = silver_receta.procesar_receta(Path(receta).read_text(encoding="utf-8"), Path(receta).name, fecha_ingesta, ejecucion_id)
    silver_receta.escribir(r, silver, cuarentena)
    tablas = gold.calcular_gold(c.precios, r.receta, i.inpc)
    for nombre, tabla in tablas.items():
        parquet.escribir_simple(destino, nombre, tabla)
    return {"silver": {"chat": c.resumen, "banxico": i.resumen, "receta": r.resumen}, "gold": {n: t.num_rows for n, t in tablas.items()}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pipeline completo en local (silver + gold).")
    ap.add_argument("--chat", type=Path, default=Path("data/sintetico/chat_proveedor.txt"))
    ap.add_argument("--receta", type=Path, default=Path("data/sintetico/receta.csv"))
    ap.add_argument("--inpc", type=Path, nargs="+", default=[
        Path("bronze_local/banxico/SP1/SP1_datos_2026-11-14.json"),
        Path("bronze_local/banxico/SP66540/SP66540_datos_2026-11-18.json"),
        Path("bronze_local/banxico/SP56386/SP56386_datos_2026-11-18.json")], help="un JSON de Banxico por serie")
    ap.add_argument("--fecha-ingesta", type=date.fromisoformat, default=date(2026, 11, 16))
    ap.add_argument("--salida", type=Path, default=Path("data/lake"))
    a = ap.parse_args()
    if not (a.chat.exists() and a.receta.exists()):
        from datos_sinteticos.generador import escribir
        escribir(a.chat.parent)
    print(json.dumps(correr(a.chat, a.receta, a.inpc, a.fecha_ingesta, a.salida), indent=2, default=str))
