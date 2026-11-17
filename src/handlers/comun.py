"""Utilidades compartidas por los handlers."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

UMBRAL_REZAGO_DIAS = 10  # una fuente semanal con datos de hace más de 10 días se reporta como atrasada


class FallaSimulada(RuntimeError):
    """Error a propósito para probar que las alertas llegan (SOW E5: falla simulada)."""


def revisar_simulacion(event: dict, etapa: str) -> None:
    if event.get("simular_falla"):
        raise FallaSimulada(f"Falla simulada a propósito en la etapa {etapa}")


def ultima_fecha(almacen, prefijo: str, hasta: date) -> date:
    """Fecha de ingesta más reciente (<= hasta) con archivos bajo `prefijo` (llaves `.../fecha_ingesta=AAAA-MM-DD/...`)."""
    fechas = []
    for llave in almacen.listar(prefijo):
        m = re.search(r"fecha_ingesta=(\d{4}-\d{2}-\d{2})/", llave)
        if m and date.fromisoformat(m.group(1)) <= hasta:
            fechas.append(date.fromisoformat(m.group(1)))
    if not fechas:
        raise FileNotFoundError(f"No hay archivos en {prefijo} con fecha_ingesta <= {hasta}")
    return max(fechas)


def hoy_cdmx(ahora: datetime | None = None) -> date:
    ahora = ahora or datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return ahora.astimezone(ZoneInfo("America/Mexico_City")).date()
    except Exception:  # sin base de zonas horarias: CDMX no tiene horario de verano desde 2022 (UTC-6)
        return (ahora.astimezone(timezone.utc) - timedelta(hours=6)).date()
