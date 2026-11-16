"""Generador de datos internos sintéticos (ADR 0007). Misma semilla, mismos datos.

Produce el chat de WhatsApp de Don Beto (un mensaje de precios por jueves, entre 6:48 y 7:15),
la receta (55 g de suadero y 50 g de pastor por taco) y las ventas diarias (200 a 400 tacos).
La serie de precios sigue las aclaraciones A1: suadero 165 a 185, pastor 138 a 155, longaniza 110 a 118.
Con `errores=True` agrega mensajes con errores intencionales para probar la cuarentena.

Uso:  python -m datos_sinteticos.generador --semilla 42 --salida data/sintetico
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

PROVEEDOR = "Don Beto"
DUENA = "Ofelia"
SERIES = {"suadero": (165, 185), "pastor": (138, 155), "longaniza": (110, 118)}
RECETA = {"suadero": 55, "pastor": 50}  # gramos por taco (aclaraciones A2)
INICIO = date(2026, 1, 1)
FIN = date(2026, 9, 30)

_SALUDOS = ["Buenos días", "Buen día Doña Ofelia", "Buenas, los precios de hoy", "Buenos días Doña Ofelia"]
_RESTO = ["lo demás igual", "lo demás sigue igual"]
_GRACIAS = ["Gracias Don Beto", "Ok, gracias", "Enterada, gracias"]


def _jueves(inicio: date, fin: date) -> list[date]:
    d = inicio + timedelta(days=(3 - inicio.weekday()) % 7)
    dias = []
    while d <= fin:
        dias.append(d)
        d += timedelta(days=7)
    return dias


def _linea(dt: datetime, remitente: str, texto: str) -> str:
    sufijo = "a. m." if dt.hour < 12 else "p. m."
    return f"{dt.day}/{dt.month}/{dt:%y}, {dt.hour % 12 or 12}:{dt.minute:02d} {sufijo} - {remitente}: {texto}"


def _trayectorias(rng: random.Random, n: int) -> tuple[dict[str, list[int]], dict[str, dict[int, int]]]:
    """Precio de cada semana y los aumentos (semana -> pesos). El precio final es exactamente el de las aclaraciones."""
    precios: dict[str, list[int]] = {}
    aumentos: dict[str, dict[int, int]] = {}
    for producto, (ini, fin) in SERIES.items():
        total = fin - ini
        k = min(total, rng.randint(4, 7))
        cortes = sorted(rng.sample(range(1, total), k - 1))
        partes = [b - a for a, b in zip([0] + cortes, cortes + [total])]
        semanas = sorted(rng.sample(range(1, n), k))
        aumentos[producto] = dict(zip(semanas, partes))
        serie, precio = [], ini
        for w in range(n):
            precio += aumentos[producto].get(w, 0)
            serie.append(precio)
        precios[producto] = serie
    return precios, aumentos


def generar_chat(semilla: int = 42, errores: bool = True, inicio: date = INICIO, fin: date = FIN) -> str:
    rng = random.Random(semilla)
    rng_err = random.Random(f"{semilla}-errores")  # aparte, para que los errores no muevan la serie
    dias = _jueves(inicio, fin)
    n = len(dias)
    precios, aumentos = _trayectorias(rng, n)

    typo_semana = rng_err.choice(sorted(aumentos["pastor"])) if errores else None
    s_cero, s_unidad, s_fecha = (rng_err.sample(range(2, n - 1), 3) if errores else (None,) * 3)

    entradas: list[tuple[datetime, str]] = []
    for w, dia in enumerate(dias):
        dt = datetime.combine(dia, time(6, 48)) + timedelta(minutes=rng.randint(0, 27))
        cambiados = [p for p in SERIES if w == 0 or aumentos[p].get(w)]
        lineas = []
        for p in cambiados:
            nombre = p.capitalize() if rng.random() < 0.5 else p
            relativo = w > 0 and rng.random() < 0.4
            estilo = rng.choice(["{n} ${p} el kilo", "{n} {p}", "{n} ${p}", "{n} a ${p}"])
            if relativo:
                lineas.append(f"el {p} subió {aumentos[p][w]} pesos")
            else:
                lineas.append(estilo.format(n=nombre, p=precios[p][w]))
            if w == typo_semana and p == "pastor":
                lineas[-1] = f"pastor ${precios[p][w] * 10}"  # error de captura, se corrige abajo
        if not cambiados:
            lineas.append("Sin cambios esta semana, todo igual")
        elif len(cambiados) < len(SERIES):
            lineas.append(rng.choice(_RESTO))
        sep = rng.choice([", ", "\n"])
        saludo = rng.choice(_SALUDOS)
        entradas.append((dt, _linea(dt, PROVEEDOR, f"{saludo}\n{sep.join(lineas)}")))

        if rng.random() < 0.35:
            t = dt + timedelta(minutes=3)
            entradas.append((t, _linea(t, DUENA, rng.choice(_GRACIAS))))
        if rng.random() < 0.15:
            t = datetime.combine(dia + timedelta(days=1), time(8, 5))
            entradas.append((t, _linea(t, PROVEEDOR, "ya va el pedido de la mañana")))

        if errores:
            extra = dt.replace(hour=7, minute=20) + timedelta(minutes=rng_err.randint(0, 5))
            if w == typo_semana:
                entradas.append((extra, _linea(extra, PROVEEDOR, f"perdón, el pastor es {precios['pastor'][w]}")))
            if w == s_cero:
                entradas.append((extra, _linea(extra, PROVEEDOR, "pastor $0")))
            if w == s_unidad:
                entradas.append((extra, _linea(extra, PROVEEDOR, f"suadero {precios['suadero'][w]} la caja")))
            if w == s_fecha:  # fecha imposible: 31 de febrero
                entradas.append((extra, f"31/2/{dia:%y}, 6:50 a. m. - {PROVEEDOR}: pastor {precios['pastor'][w]}"))

    entradas.sort(key=lambda e: e[0])
    return "\n".join(texto for _, texto in entradas) + "\n"


def generar_receta() -> list[dict]:
    return [{"producto": p, "gramos_por_taco": g} for p, g in RECETA.items()]


def generar_ventas(semilla: int = 42, inicio: date = INICIO, fin: date = FIN) -> list[dict]:
    """Tacos vendidos por día (200 en un día malo, 400 en uno bueno; aclaraciones A4). Dato de apoyo, no entra al índice."""
    rng = random.Random(f"{semilla}-ventas")
    return [{"fecha": inicio + timedelta(days=i), "tacos": rng.randint(200, 400)}
            for i in range((fin - inicio).days + 1)]


def escribir(salida: Path, semilla: int = 42, errores: bool = True) -> list[Path]:
    salida.mkdir(parents=True, exist_ok=True)
    chat = salida / "chat_proveedor.txt"
    chat.write_text(generar_chat(semilla, errores), encoding="utf-8")
    receta, ventas = salida / "receta.csv", salida / "ventas_diarias.csv"
    for ruta, filas in ((receta, generar_receta()), (ventas, generar_ventas(semilla))):
        with ruta.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
    return [chat, receta, ventas]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Genera los datos internos sintéticos del Índice del Taco.")
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--salida", type=Path, default=Path("data/sintetico"))
    ap.add_argument("--sin-errores", action="store_true", help="no agrega los errores intencionales")
    args = ap.parse_args()
    for ruta in escribir(args.salida, args.semilla, not args.sin_errores):
        print(ruta)
