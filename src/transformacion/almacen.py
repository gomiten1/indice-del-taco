"""Almacén de archivos con la misma interfaz para disco y S3: el código de silver/gold no sabe cuál usa.

Las rutas son relativas y con `/` (como las llaves de S3). `listar(prefijo)` sigue la semántica de S3:
devuelve todas las llaves que empiezan con el prefijo (pasa el prefijo con `/` final para una carpeta).
"""
from __future__ import annotations

from pathlib import Path


class AlmacenLocal:
    def __init__(self, raiz):
        self.raiz = Path(raiz)

    def put(self, ruta: str, datos: bytes) -> None:
        destino = self.raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(datos)

    def get(self, ruta: str) -> bytes:
        return (self.raiz / ruta).read_bytes()

    def abrir(self, ruta: str):
        """Flujo de lectura sin cargar todo el archivo en memoria (para los CSV grandes de PROFECO)."""
        return (self.raiz / ruta).open("rb")

    def listar(self, prefijo: str) -> list[str]:
        if not self.raiz.exists():
            return []
        return sorted(p.relative_to(self.raiz).as_posix() for p in self.raiz.rglob("*")
                      if p.is_file() and p.relative_to(self.raiz).as_posix().startswith(prefijo))

    def borrar(self, ruta: str) -> None:
        archivo = self.raiz / ruta
        archivo.unlink()
        for carpeta in archivo.parents:  # limpia carpetas que quedaron vacías, sin salir de la raíz
            if carpeta == self.raiz or any(carpeta.iterdir()):
                break
            carpeta.rmdir()


class AlmacenS3:
    def __init__(self, s3, bucket: str):
        self.s3, self.bucket = s3, bucket

    def put(self, ruta: str, datos: bytes) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=ruta, Body=datos)

    def get(self, ruta: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=ruta)["Body"].read()

    def abrir(self, ruta: str):
        """Flujo de lectura de S3 sin cargar todo el archivo en memoria (para los CSV grandes de PROFECO)."""
        return self.s3.get_object(Bucket=self.bucket, Key=ruta)["Body"]

    def listar(self, prefijo: str) -> list[str]:
        llaves, token = [], None
        while True:
            args = {"Bucket": self.bucket, "Prefix": prefijo}
            if token:
                args["ContinuationToken"] = token
            r = self.s3.list_objects_v2(**args)
            llaves += [o["Key"] for o in r.get("Contents", [])]
            token = r.get("NextContinuationToken")
            if not token:
                return sorted(llaves)

    def borrar(self, ruta: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=ruta)
