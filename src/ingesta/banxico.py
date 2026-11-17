"""Lambda de ingesta de Banxico SIE hacia bronze (E2, tarea 1.3).

Descarga cada serie tal cual la entrega Banxico (sin transformar) y la guarda en S3 bajo
`raw/banxico/<serie>/fecha_ingesta=AAAA-MM-DD/`. Ejecutarla dos veces el mismo día escribe en
las mismas llaves y, si el contenido no cambió, ni siquiera se reescribe. Solo usa la biblioteca estándar y boto3 (que ya
viene en el runtime de Lambda); el token nunca se escribe en logs ni en mensajes de error.

Variables de entorno:
  BRONZE_BUCKET        bucket de la capa bronze (obligatoria)
  BANXICO_TOKEN_PARAM  nombre del parámetro SecureString de SSM con el token (en AWS)
  BANXICO_TOKEN        token directo (solo pruebas locales; si está, tiene prioridad)
  BANXICO_SERIES       series separadas por coma (por defecto SP1, INPC general)

Evento opcional: {"fecha_ingesta": "AAAA-MM-DD", "series": ["SP1"]} para repetir una fecha.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError

BASE_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"
SERIES_POR_DEFECTO = ("SP1",)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class IngestaError(Exception):
    """Falla que debe detener la ejecución y disparar la alarma (nunca se guarda un dato dudoso)."""


def url_datos(serie: str) -> str:
    return f"{BASE_URL}/{serie}/datos"


def url_metadatos(serie: str) -> str:
    return f"{BASE_URL}/{serie}"


def clave_s3(serie: str, fecha_ingesta: str, tipo: str) -> str:
    return f"raw/banxico/{serie}/fecha_ingesta={fecha_ingesta}/{serie}_{tipo}.json"


def descargar(url: str, token: str, timeout: int = 20, abrir=urllib.request.urlopen) -> bytes:
    req = urllib.request.Request(url, headers={"Bmx-Token": token, "Accept": "application/json"})
    try:
        with abrir(req, timeout=timeout) as respuesta:
            return respuesta.read()
    except HTTPError as e:  # 400 incluye el límite de consultas (secondsToReset)
        raise IngestaError(f"Banxico respondió HTTP {e.code} para {url}") from None
    except (URLError, TimeoutError) as e:
        raise IngestaError(f"No se pudo conectar con Banxico ({url}): {e}") from None


def validar_datos(serie: str, cuerpo: bytes) -> int:
    """Confirma que la respuesta trae la serie pedida con datos. Devuelve cuántas observaciones hay."""
    try:
        series = json.loads(cuerpo)["bmx"]["series"]
        encontrada = series[0]
    except (ValueError, KeyError, IndexError, TypeError):
        raise IngestaError(f"Respuesta inesperada de Banxico para {serie} (no trae bmx.series)") from None
    if encontrada.get("idSerie") != serie:
        raise IngestaError(f"Banxico devolvió la serie {encontrada.get('idSerie')} y se pidió {serie}")
    datos = encontrada.get("datos")
    if not datos:
        raise IngestaError(f"La serie {serie} llegó sin datos")
    return len(datos)


def _ya_esta_igual(s3, bucket: str, clave: str, cuerpo: bytes) -> bool:
    """True si la llave ya existe con el mismo contenido. Para cargas de una parte con SSE-S3 el ETag es el MD5."""
    try:
        etag = s3.head_object(Bucket=bucket, Key=clave)["ETag"].strip('"')
    except Exception as e:  # ClientError de boto3 (no se importa aquí para poder probar sin boto3)
        codigo = getattr(e, "response", {}).get("Error", {}).get("Code")
        if codigo in ("404", "NoSuchKey", "NotFound"):
            return False
        raise  # un 403 u otro error real no se confunde con "no existe"
    return etag == hashlib.md5(cuerpo).hexdigest()


def ingestar_serie(serie: str, fecha_ingesta: str, token: str, bucket: str, s3,
                   abrir=urllib.request.urlopen) -> dict:
    datos = descargar(url_datos(serie), token, abrir=abrir)
    registros = validar_datos(serie, datos)  # primero se valida; si falla no se escribe nada
    metadatos = descargar(url_metadatos(serie), token, abrir=abrir)
    claves, escritas, omitidas = [], [], []
    for tipo, cuerpo in (("datos", datos), ("metadatos", metadatos)):
        clave = clave_s3(serie, fecha_ingesta, tipo)
        claves.append(clave)
        if _ya_esta_igual(s3, bucket, clave, cuerpo):
            omitidas.append(clave)  # mismo contenido: no se reescribe (evita versiones repetidas)
        else:
            s3.put_object(Bucket=bucket, Key=clave, Body=cuerpo, ContentType="application/json")
            escritas.append(clave)
    return {"serie": serie, "registros": registros, "bytes": len(datos),
            "claves": claves, "escritas": escritas, "omitidas": omitidas}


def obtener_token(ssm=None) -> str:
    token = os.environ.get("BANXICO_TOKEN")
    if token:
        return token
    parametro = os.environ.get("BANXICO_TOKEN_PARAM")
    if not parametro:
        raise IngestaError("Falta el token: define BANXICO_TOKEN_PARAM (o BANXICO_TOKEN en pruebas)")
    if ssm is None:
        import boto3  # solo en AWS; las pruebas locales no lo necesitan
        ssm = boto3.client("ssm")
    return ssm.get_parameter(Name=parametro, WithDecryption=True)["Parameter"]["Value"]


def handler(event, context, s3=None, abrir=urllib.request.urlopen, ssm=None) -> dict:
    event = event or {}
    if event.get("simular_falla"):
        raise IngestaError("Falla simulada a propósito en la etapa ingesta")
    bucket = os.environ.get("BRONZE_BUCKET")
    if not bucket:
        raise IngestaError("Falta la variable de entorno BRONZE_BUCKET")

    fecha = event.get("fecha_ingesta") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        raise IngestaError(f"fecha_ingesta debe ser AAAA-MM-DD, llegó {fecha!r}") from None

    series = event.get("series") or [s.strip() for s in os.environ.get("BANXICO_SERIES", "").split(",") if s.strip()] \
        or list(SERIES_POR_DEFECTO)
    token = obtener_token(ssm)
    if s3 is None:
        import boto3
        s3 = boto3.client("s3")

    resultados = [ingestar_serie(s, fecha, token, bucket, s3, abrir) for s in series]
    logger.info("Banxico: fecha_ingesta=%s series=%s", fecha, [(r["serie"], r["registros"]) for r in resultados])
    return {"fuente": "banxico", "fecha_ingesta": fecha, "series": resultados}
