"""Silver de PROFECO («Quién es quién en los precios»): CSV de bronze -> Parquet particionado, solo CDMX y solo los insumos del taco.

Decisiones: ADR 0015 (qué producto de PROFECO equivale a cada insumo), ADR 0020 (se usa el CSV descargado a mano y se registra
hasta qué día llegan los datos) y ADR 0021 (unidades, calidad y duplicados). El archivo pesa unos 220 MB, así que se lee en
bloques (nunca entero en memoria) y se filtra con operaciones vectorizadas antes de revisar fila por fila.

La cobertura (`fecha_min`, `fecha_max`) se calcula sobre las filas que SÍ se usan: es el periodo real que respalda a P2 y P3.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pcsv

from transformacion import parquet
from transformacion.comun import ESQUEMA_CUARENTENA, EsquemaInesperado, armar_resumen, fila_cuarentena

FUENTE = "profeco"
TABLA_SILVER = "silver_precio_mercado"
ESTADO = "Ciudad de México"
COLUMNAS = ["producto", "presentacion", "marca", "precio", "fecha_registro", "cadena_comercial", "giro",
            "nombre_comercial", "direccion", "estado", "municipio"]

# (producto en PROFECO, condición sobre la presentación, insumo, equivalencia). «proxy» = el corte más parecido, no el mismo (ADR 0015).
REGLAS = [
    ("Carne Cerdo", lambda p: "Pierna Entera Sin Hueso" in p, "pastor", "proxy"),
    ("Carne Res", lambda p: "Falda" in p, "suadero", "proxy"),
    ("Carne Cerdo", lambda p: "Longaniza" in p, "longaniza", "exacta"),
    ("Tortilla de Maíz", lambda p: re.match(r"(Bolsa )?1 Kg", p) is not None, "tortilla", "exacta"),
    ("Cebolla", lambda p: "1 Kg" in p and "Blanca" in p, "cebolla", "exacta"),
    ("Limón", lambda p: "1 Kg" in p, "limon", "exacta"),
    ("Piña", lambda p: "1 Kg" in p, "pina", "exacta"),
    ("Cilantro", lambda p: p.strip() == "Manojo", "cilantro", "exacta"),
]
PRODUCTOS = sorted({r[0] for r in REGLAS})
_KILOS = re.compile(r"^(?:bolsa\s+)?(\d+(?:[.,]\d+)?)\s*kg\b", re.I)

ESQUEMA_MERCADO = pa.schema([
    ("fecha_registro", pa.date32()), ("anio", pa.int32()), ("semana_iso", pa.int32()), ("producto_original", pa.string()),
    ("insumo", pa.string()), ("equivalencia", pa.string()), ("presentacion", pa.string()), ("marca", pa.string()),
    ("precio", pa.decimal128(10, 2)), ("precio_kg", pa.decimal128(10, 2)), ("canal", pa.string()), ("cadena_comercial", pa.string()),
    ("nombre_comercial", pa.string()), ("direccion", pa.string()), ("municipio", pa.string()), ("archivo_origen", pa.string()),
    ("fecha_ingesta", pa.date32())])
_CLAVE = ("producto_original", "presentacion", "marca", "nombre_comercial", "direccion", "fecha_registro")


@dataclass(frozen=True)
class ResultadoMercado:
    mercado: pa.Table
    cuarentena: pa.Table
    resumen: dict
    archivo_origen: str
    fecha_ingesta: date


def clasificar(producto: str, presentacion: str):
    """(insumo, equivalencia) si el producto de PROFECO equivale a un insumo del taco; si no, None."""
    for nombre, condicion, insumo, equivalencia in REGLAS:
        if producto == nombre and condicion(presentacion):
            return insumo, equivalencia
    return None


def precio_kg(presentacion: str, precio: Decimal) -> Decimal | None:
    """Precio por kilo si la presentación viene en kilos; en manojos o piezas es None (no se inventa el peso)."""
    m = _KILOS.match(presentacion.strip())
    if not m:
        return None
    kilos = Decimal(m.group(1).replace(",", "."))
    return (precio / kilos).quantize(Decimal("0.01")) if kilos > 0 else None


def _q(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"))


def _deduplicar(filas: list[dict]) -> tuple[list[dict], int]:
    """Una fila por tienda, producto y día; si repiten con precios distintos, la mediana (ADR 0021)."""
    grupos: dict[tuple, list[dict]] = {}
    for f in filas:
        grupos.setdefault(tuple(f[c] for c in _CLAVE), []).append(f)
    salida, sobrantes = [], 0
    for grupo in grupos.values():
        sobrantes += len(grupo) - 1
        fila = dict(grupo[0])
        if len({g["precio"] for g in grupo}) > 1:
            fila["precio"] = _q(statistics.median(g["precio"] for g in grupo))
            fila["precio_kg"] = precio_kg(fila["presentacion"], fila["precio"])
        salida.append(fila)
    salida.sort(key=lambda f: (f["fecha_registro"], f["insumo"], f["canal"], f["nombre_comercial"], f["direccion"], f["presentacion"], f["marca"], f["precio"]))
    return salida, sobrantes


def _resultado(filas, cuarentena, extras: dict, leidos: int, sobrantes: int, archivo_origen: str, fecha_ingesta: date) -> ResultadoMercado:
    resumen = armar_resumen(leidos, len(filas), len(cuarentena))
    fechas = [f["fecha_registro"] for f in filas]
    resumen.update({**extras, "duplicados": sobrantes, "fecha_min": str(min(fechas)) if fechas else None, "fecha_max": str(max(fechas)) if fechas else None})
    return ResultadoMercado(pa.Table.from_pylist(filas, schema=ESQUEMA_MERCADO), pa.Table.from_pylist(cuarentena, schema=ESQUEMA_CUARENTENA),
                            resumen, archivo_origen, fecha_ingesta)


def procesar_profeco(flujo, archivo_origen: str, fecha_ingesta: date, ejecucion_id: str) -> ResultadoMercado:
    """`flujo`: archivo abierto en binario (disco o S3). Se lee por bloques."""
    try:
        lector = pcsv.open_csv(
            flujo, read_options=pcsv.ReadOptions(block_size=8 * 1024 * 1024),
            convert_options=pcsv.ConvertOptions(include_columns=COLUMNAS, column_types={c: pa.string() for c in COLUMNAS}, strings_can_be_null=False))
    except (pa.ArrowException, KeyError) as e:
        raise EsquemaInesperado(f"{archivo_origen}: faltan columnas esperadas de PROFECO ({e})") from None

    filas, cuarentena = [], []
    filas_csv = filas_cdmx = leidos = 0
    productos = pa.array(PRODUCTOS)
    for lote in lector:
        filas_csv += lote.num_rows
        cdmx = lote.filter(pc.equal(lote["estado"], ESTADO))
        filas_cdmx += cdmx.num_rows
        for f in cdmx.filter(pc.is_in(cdmx["producto"], value_set=productos)).to_pylist():
            clasificado = clasificar(f["producto"], f["presentacion"])
            if clasificado is None:
                continue
            leidos += 1
            insumo, equivalencia = clasificado
            original = ",".join(f"{f[c]}" for c in COLUMNAS)

            def rechazar(regla, motivo):
                cuarentena.append(fila_cuarentena(FUENTE, regla, motivo, original, archivo_origen, None, ejecucion_id, fecha_ingesta))

            try:
                precio = Decimal(f["precio"].strip())
                if not precio.is_finite() or precio <= 0:
                    raise InvalidOperation
            except InvalidOperation:
                rechazar("precio_invalido", f"precio no válido: {f['precio']!r}")
                continue
            try:
                dia = datetime.strptime(f["fecha_registro"].strip(), "%Y-%m-%d").date()
            except ValueError:
                rechazar("fecha_invalida", f"fecha no válida: {f['fecha_registro']!r}")
                continue
            precio = _q(precio)
            iso = dia.isocalendar()
            filas.append({
                "fecha_registro": dia, "anio": iso.year, "semana_iso": iso.week, "producto_original": f["producto"], "insumo": insumo,
                "equivalencia": equivalencia, "presentacion": f["presentacion"], "marca": f["marca"], "precio": precio,
                "precio_kg": precio_kg(f["presentacion"], precio), "canal": "mayoreo" if f["giro"] == "Central de Abasto" else "menudeo",
                "cadena_comercial": f["cadena_comercial"], "nombre_comercial": f["nombre_comercial"], "direccion": f["direccion"],
                "municipio": f["municipio"], "archivo_origen": archivo_origen, "fecha_ingesta": fecha_ingesta})
    filas, sobrantes = _deduplicar(filas)
    return _resultado(filas, cuarentena, {"filas_csv": filas_csv, "filas_cdmx": filas_cdmx}, leidos, sobrantes, archivo_origen, fecha_ingesta)


def combinar(resultados: list[ResultadoMercado]) -> ResultadoMercado:
    """Junta varios archivos (quincenas) y deduplica entre ellos. Hace falta porque silver REEMPLAZA la tabla completa al escribir."""
    if not resultados:
        raise ValueError("No hay archivos de PROFECO para combinar")
    filas, cuarentena = [], []
    for r in resultados:
        filas += r.mercado.to_pylist()
        cuarentena += r.cuarentena.to_pylist()
    filas, entre_archivos = _deduplicar(filas)
    suma = lambda clave: sum(r.resumen[clave] for r in resultados)
    return _resultado(filas, cuarentena, {"filas_csv": suma("filas_csv"), "filas_cdmx": suma("filas_cdmx")}, suma("leidos"),
                      suma("duplicados") + entre_archivos, "archivos_profeco.csv", max(r.fecha_ingesta for r in resultados))


def escribir(resultado: ResultadoMercado, silver, cuarentena) -> list[str]:
    rutas = parquet.escribir_particionada(silver, TABLA_SILVER, resultado.mercado, ["anio", "semana_iso"],
                                          lambda anio, semana: f"anio={anio}/semana_iso={semana:02d}")
    rutas.append(parquet.escribir_cuarentena(cuarentena, FUENTE, resultado.fecha_ingesta, resultado.archivo_origen, resultado.cuarentena))
    return rutas
