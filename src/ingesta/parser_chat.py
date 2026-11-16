"""Parser del chat de WhatsApp del proveedor exportado como .txt.

Resuelve los casos C1 a C11 del ADR 0007: precios con y sin `$`, unidad implícita,
cambios relativos, correcciones, "lo demás igual", mensajes sin precios o de la dueña,
y rechaza a cuarentena precios inválidos, unidades desconocidas y fechas inválidas.

No lee nada de red ni de disco: recibe el texto y devuelve dos listas
(`precios` y `rechazos`). Es determinista, así que reprocesar el mismo chat da lo mismo.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

REMITENTE_PROVEEDOR = "Don Beto"
UNIDAD_IMPLICITA = "kg"

# Catálogo ampliable: alias normalizado (minúsculas, sin acentos) -> nombre canónico.
PRODUCTOS = {"pastor": "pastor", "suadero": "suadero", "longaniza": "longaniza"}

UNIDADES = {
    "kilo": "kg", "kilos": "kg", "kg": "kg", "kgs": "kg",
    "pieza": "pieza", "piezas": "pieza", "pza": "pieza", "pzas": "pieza", "pz": "pieza",
    "paquete": "paquete", "paquetes": "paquete",
}
# Unidades que se reconocen pero no se pueden convertir a kg/pieza: van a cuarentena
# y la alerta pide ampliar el catálogo (SOW, reglas de calidad).
UNIDADES_NO_SOPORTADAS = {
    "caja", "cajas", "bulto", "bultos", "costal", "costales", "tonelada", "toneladas",
    "litro", "litros", "bolsa", "bolsas", "charola", "charolas", "cubeta", "cubetas",
    "docena", "docenas", "gramo", "gramos",
}

_ENCABEZADO = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{2,4}),\s+(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?\s+-\s+(.*)$", re.I)
_RE_PRODUCTO = re.compile(r"\b(" + "|".join(PRODUCTOS) + r")\b")
_RE_NUMERO = re.compile(r"(-?)(?:\$\s?)?(\d+(?:[.,]\d{1,2})?)")
_RE_CAMBIO = re.compile(r"\b(subio|subieron|subimos|sube|aumento|aumentaron|bajo|bajaron|bajamos|baja|rebajo)\b")
_BAJAS = {"bajo", "bajaron", "bajamos", "baja", "rebajo"}
_RE_CORRECCION = re.compile(r"\b(perdon|perdona|correccion|corrijo|me equivoque|rectifico)\b")
_RE_RESTO = re.compile(
    r"\b(?:demas|resto)\b.{0,20}\b(?:igual|sin cambios?|mismo)\b|\bsin cambios?\b|\btodo (?:sigue |queda |se queda )?igual\b")
_RE_ABSOLUTO_ANTES = re.compile(r"\ba\s*\$?\s*$")
_RE_UNIDAD = re.compile(r"\b(" + "|".join(UNIDADES) + r")\b")
_RE_UNIDAD_NO_SOPORTADA = re.compile(r"\b(" + "|".join(UNIDADES_NO_SOPORTADAS) + r")\b")
_SEPARADOR_CLAUSULAS = re.compile(r"(?<=[.,;!?])\s+|\n+|\s+y\s+")


@dataclass(frozen=True)
class PrecioProveedor:
    fecha: datetime
    producto: str
    precio: Decimal
    unidad: str
    tipo: str  # explicito | relativo | correccion | repetido
    linea: int


@dataclass(frozen=True)
class Rechazo:
    linea: int
    fecha: datetime | None
    motivo: str  # precio_invalido | unidad_desconocida | fecha_invalida | cambio_relativo_sin_base
    detalle: str
    texto: str


@dataclass(frozen=True)
class ResultadoParseo:
    precios: list[PrecioProveedor]
    rechazos: list[Rechazo]


@dataclass
class _Mensaje:
    linea: int
    fecha: datetime | None
    remitente: str
    lineas: list[str]


def _normalizar(texto: str) -> str:
    sin_acentos = "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))
    return sin_acentos


def _limpiar(texto: str) -> str:
    for raro in ("‎", "‏", "﻿"):
        texto = texto.replace(raro, "")
    return texto.replace(" ", " ").replace(" ", " ")


def _fecha(d: str, m: str, a: str, h: str, mi: str, ampm: str) -> datetime | None:
    anio = int(a) + 2000 if len(a) == 2 else int(a)
    hora = int(h)
    if not 1 <= hora <= 12:
        return None
    hora = (0 if hora == 12 else hora) + (12 if ampm.lower() == "p" else 0)
    try:
        return datetime(anio, int(m), int(d), hora, int(mi))
    except ValueError:
        return None


def _dinero(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _leer_mensajes(texto: str) -> list[_Mensaje]:
    mensajes: list[_Mensaje] = []
    actual: _Mensaje | None = None
    for n, linea in enumerate(_limpiar(texto).splitlines(), start=1):
        m = _ENCABEZADO.match(linea)
        if m:
            d, mes, a, h, mi, ampm, resto = m.groups()
            remitente, sep, cuerpo = resto.partition(": ")
            if not sep:  # línea de sistema ("Los mensajes están cifrados...")
                actual = None
                continue
            actual = _Mensaje(n, _fecha(d, mes, a, h, mi, ampm), remitente.strip(), [cuerpo])
            mensajes.append(actual)
        elif actual is not None:
            actual.lineas.append(linea)
    return mensajes


def _unidad(resto: str) -> tuple[str | None, str | None]:
    """Devuelve (unidad canónica, unidad no soportada). Si ninguna aparece, la unidad es implícita."""
    if (m := _RE_UNIDAD_NO_SOPORTADA.search(resto)):
        return None, m.group(1)
    if (m := _RE_UNIDAD.search(resto)):
        return UNIDADES[m.group(1)], None
    return UNIDAD_IMPLICITA, None


def _analizar(producto: str, seg: str, vigentes: dict[str, tuple[Decimal, str]]):
    """Un producto y el texto que le sigue. Devuelve (producto, precio, unidad, tipo), un rechazo (motivo, detalle) o None."""
    num = _RE_NUMERO.search(seg)
    if num is None:
        return None  # menciona el producto sin precio: no es error
    try:
        monto = Decimal(num.group(2).replace(",", "."))
    except InvalidOperation:
        return None
    if num.group(1):
        monto = -monto

    cue = _RE_CAMBIO.search(seg)
    if cue and not _RE_ABSOLUTO_ANTES.search(seg[: num.start()]):
        if producto not in vigentes:
            return ("cambio_relativo_sin_base", f"{producto}: no hay precio previo")
        base, unidad = vigentes[producto]
        signo = -1 if cue.group(1) in _BAJAS else 1
        es_porcentaje = seg[num.end():].lstrip().startswith("%")
        nuevo = base * (1 + signo * monto / 100) if es_porcentaje else base + signo * monto
        if nuevo <= 0:
            return ("precio_invalido", f"{producto}: el cambio deja el precio en {_dinero(nuevo)}")
        return (producto, _dinero(nuevo), unidad, "relativo")

    if monto <= 0:
        return ("precio_invalido", f"{producto}: precio {monto}")
    unidad, no_soportada = _unidad(seg[num.end():])
    if no_soportada:
        return ("unidad_desconocida", f"{producto}: unidad '{no_soportada}'")
    return (producto, _dinero(monto), unidad, "explicito")


def _extraer(cuerpo: str, vigentes: dict[str, tuple[Decimal, str]]):
    """Procesa un mensaje. Modifica `vigentes` (una copia de trabajo). Devuelve (items, fallas, es_correccion)."""
    norm = _normalizar(cuerpo)
    es_correccion = bool(_RE_CORRECCION.search(norm))
    items: list[tuple[str, Decimal, str, str]] = []
    fallas: list[tuple[str, str]] = []
    mencionados: set[str] = set()
    pide_resto = False

    for clausula in _SEPARADOR_CLAUSULAS.split(norm):
        if _RE_RESTO.search(clausula):
            pide_resto = True
        menciones = list(_RE_PRODUCTO.finditer(clausula))
        for i, m in enumerate(menciones):
            fin = menciones[i + 1].start() if i + 1 < len(menciones) else len(clausula)
            producto = PRODUCTOS[m.group(1)]
            r = _analizar(producto, clausula[m.end():fin], vigentes)
            if r is None:
                continue
            mencionados.add(producto)
            if r[0] in ("precio_invalido", "unidad_desconocida", "cambio_relativo_sin_base"):
                fallas.append(r)
            else:
                items.append(r)
                vigentes[r[0]] = (r[1], r[2])

    if pide_resto:
        for producto in PRODUCTOS.values():
            if producto not in mencionados and producto in vigentes:
                precio, unidad = vigentes[producto]
                items.append((producto, precio, unidad, "repetido"))
    return items, fallas, es_correccion


def parsear_chat(texto: str, remitente_proveedor: str = REMITENTE_PROVEEDOR) -> ResultadoParseo:
    precios: list[PrecioProveedor] = []
    rechazos: list[Rechazo] = []
    vigentes: dict[str, tuple[Decimal, str]] = {}

    for msg in _leer_mensajes(texto):
        if msg.remitente != remitente_proveedor:
            continue
        cuerpo = "\n".join(msg.lineas)
        trabajo = dict(vigentes)
        items, fallas, es_correccion = _extraer(cuerpo, trabajo)

        if msg.fecha is None:
            if items or fallas:  # trae precios pero no se puede fechar: todo el mensaje a cuarentena
                rechazos.append(Rechazo(msg.linea, None, "fecha_invalida", "fecha no válida en el encabezado", cuerpo))
            continue

        for motivo, detalle in fallas:
            rechazos.append(Rechazo(msg.linea, msg.fecha, motivo, detalle, cuerpo))
        for producto, precio, unidad, tipo in items:
            nuevo = PrecioProveedor(msg.fecha, producto, precio, unidad, tipo, msg.linea)
            previos = [i for i, p in enumerate(precios) if p.producto == producto]
            if es_correccion and tipo == "explicito" and previos:
                i = previos[-1]  # la corrección reemplaza el último precio y queda vigente desde el aviso original
                precios[i] = replace(precios[i], precio=precio, unidad=unidad, tipo="correccion")
            else:
                precios.append(nuevo)
        vigentes = trabajo

    return ResultadoParseo(precios, rechazos)
