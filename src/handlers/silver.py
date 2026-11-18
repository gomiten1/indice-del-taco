"""Lambda de silver: lee de bronze el chat, el INPC de Banxico, la receta y (si hay) los CSV de PROFECO, y escribe silver y cuarentena.

Evento opcional: {"fecha_ingesta": "AAAA-MM-DD", "ejecucion_id": "...", "simular_falla": true}.
Banxico puede traer varias series (SP1 es obligatoria); se combinan en una sola tabla.
Cada fuente se lee de su archivo MÁS RECIENTE con fecha <= fecha_ingesta (el chat y la receta no se suben cada semana).
Las fechas usadas se devuelven en `fechas_origen`; si el chat o Banxico están atrasados más de UMBRAL_REZAGO_DIAS,
`alertas` lo dice (regla de completitud por fuente). Variables de entorno: BRONZE_BUCKET, SILVER_BUCKET, QUARANTINE_BUCKET.
Si falta un archivo de bronze o tiene una forma inesperada, la Lambda falla (y esa falla dispara la alarma).
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone

from handlers.comun import UMBRAL_REZAGO_DIAS, revisar_simulacion, ultima_fecha
from transformacion import silver_chat, silver_inpc, silver_mercado, silver_receta
from transformacion.almacen import AlmacenS3
from transformacion.comun import UMBRAL_CUARENTENA


SERIE_OBLIGATORIA = "SP1"  # INPC general: base de P4; sin ella la corrida falla. Las demás series (alimentos, pecuarios) son opcionales


def series_en_bronze(bronze) -> list[str]:
    """Series de Banxico que tienen datos en bronze (`raw/banxico/<serie>/fecha_ingesta=.../<serie>_datos.json`)."""
    return sorted({m.group(1) for llave in bronze.listar("raw/banxico/")
                   if (m := re.match(r"raw/banxico/([^/]+)/fecha_ingesta=[^/]+/\1_datos\.json$", llave))})


def csv_profeco_en_bronze(bronze, hasta: date) -> list[tuple[date, str]]:
    """CSV de PROFECO (`raw/profeco/fecha_ingesta=.../*.csv`) con fecha <= `hasta`, ordenados; todos se combinan (silver reemplaza la tabla completa)."""
    salida = []
    for llave in bronze.listar("raw/profeco/"):
        m = re.match(r"raw/profeco/fecha_ingesta=(\d{4}-\d{2}-\d{2})/[^/]+\.csv$", llave)
        if m and date.fromisoformat(m.group(1)) <= hasta:
            salida.append((date.fromisoformat(m.group(1)), llave))
    return sorted(salida)


def fecha_del_evento(event: dict) -> date:
    texto = event.get("fecha_ingesta") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"fecha_ingesta debe ser AAAA-MM-DD, llegó {texto!r}") from None


def handler(event, context, s3=None) -> dict:
    event = event or {}
    revisar_simulacion(event, "silver")
    fecha = fecha_del_evento(event)
    ejecucion = event.get("ejecucion_id") or getattr(context, "aws_request_id", None) or f"silver-{fecha}"
    if s3 is None:
        import boto3
        s3 = boto3.client("s3")
    bronze, silver, cuarentena = (AlmacenS3(s3, os.environ[v]) for v in ("BRONZE_BUCKET", "SILVER_BUCKET", "QUARANTINE_BUCKET"))

    f_chat = ultima_fecha(bronze, "raw/chat/", fecha)
    fechas_series = {SERIE_OBLIGATORIA: ultima_fecha(bronze, f"raw/banxico/{SERIE_OBLIGATORIA}/", fecha)}
    for serie in series_en_bronze(bronze):
        if serie != SERIE_OBLIGATORIA:
            try:
                fechas_series[serie] = ultima_fecha(bronze, f"raw/banxico/{serie}/", fecha)
            except FileNotFoundError:
                continue  # esa serie solo tiene archivos de fechas posteriores
    f_receta = ultima_fecha(bronze, "raw/interno/", fecha)

    chat = silver_chat.procesar_chat(bronze.get(f"raw/chat/fecha_ingesta={f_chat}/chat_proveedor.txt").decode("utf-8"),
                                     "chat_proveedor.txt", f_chat, ejecucion)
    silver_chat.escribir(chat, silver, cuarentena)
    inpc = silver_inpc.combinar([
        silver_inpc.procesar_inpc(bronze.get(f"raw/banxico/{s}/fecha_ingesta={f}/{s}_datos.json"), f"{s}_datos.json", f, ejecucion)
        for s, f in sorted(fechas_series.items())])  # se juntan antes de escribir: silver reemplaza la tabla completa
    silver_inpc.escribir(inpc, silver, cuarentena)
    receta = silver_receta.procesar_receta(bronze.get(f"raw/interno/fecha_ingesta={f_receta}/receta.csv").decode("utf-8"),
                                           "receta.csv", f_receta, ejecucion)
    silver_receta.escribir(receta, silver, cuarentena)

    fuentes = {"chat": chat.resumen, "banxico": inpc.resumen, "receta": receta.resumen}
    profeco_fechas = csv_profeco_en_bronze(bronze, fecha)
    if profeco_fechas:  # opcional (ADR 0020): se carga a mano; si no hay CSV, P2 simplemente queda sin mercado
        mercado = silver_mercado.combinar([
            silver_mercado.procesar_profeco(bronze.abrir(llave), llave.rsplit("/", 1)[-1], f, ejecucion) for f, llave in profeco_fechas])
        silver_mercado.escribir(mercado, silver, cuarentena)
        fuentes["profeco"] = mercado.resumen
    alertas = [f"{n}: cuarentena de {r['proporcion_cuarentena']:.0%} (umbral {UMBRAL_CUARENTENA:.0%})"
               for n, r in fuentes.items() if r["alerta_cuarentena"]]
    atrasos = [("chat", f_chat)] + [(f"banxico: {s}", f) for s, f in sorted(fechas_series.items())]  # la receta casi no cambia: no cuenta
    for nombre, origen in atrasos:
        dias = (fecha - origen).days
        if dias > UMBRAL_REZAGO_DIAS:
            alertas.append(f"{nombre} con datos de hace {dias} dias (mas de {UMBRAL_REZAGO_DIAS})" if nombre.startswith("banxico")
                           else f"{nombre}: datos de hace {dias} dias (mas de {UMBRAL_REZAGO_DIAS})")
    return {"etapa": "silver", "fecha_ingesta": str(fecha), "ejecucion_id": ejecucion, "fuentes": fuentes, "alertas": alertas,
            "fechas_origen": {"chat": str(f_chat), "banxico": str(min(fechas_series.values())), "receta": str(f_receta)},
            "cobertura_profeco": ({"desde": fuentes["profeco"]["fecha_min"], "hasta": fuentes["profeco"]["fecha_max"]} if "profeco" in fuentes else None),
            "fechas_series_banxico": {s: str(f) for s, f in sorted(fechas_series.items())}}
