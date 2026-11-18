"""Gold: costo por taco e Índice del Taco (P1), precio semanal por insumo y comparación con la inflación (P4).

Contrato: docs/diccionario_datos.md. La inflación de alimentos (N4) sale de las series SP66540 y SP56386 de Banxico. Decisiones: ADR 0003 (precio del proveedor = último precio vigente de la
semana), 0005 (la salsa no entra; el costo cuenta solo los insumos con dato), 0008 (merma solo en pastor, como
versión aparte) y 0009 (semana base = primera semana con todos los insumos de la receta).

Lógica pura sobre tablas de pyarrow: no sabe de disco ni de S3. Queda pendiente `comparativo_proveedor` (P2),
que necesita los precios de PROFECO. `contribucion_insumo` (P3) ya se calcula, pero los insumos sin precio salen
como "sin dato" (nunca se inventa un aporte de 0 %).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

import pyarrow as pa

# Series del INPC de Banxico (docs/fuentes.md). General, alimentos (subyacente: productos procesados) y pecuarios (no subyacente: más volátil).
SERIE_GENERAL, SERIE_ALIMENTOS, SERIE_PECUARIOS = "SP1", "SP66540", "SP56386"

MERMA_PASTOR = Decimal("0.12")  # ADR 0008: parte del trompo que no se vende (≈12 %)

# Insumos que forman cada taco según el SOW (la salsa queda fuera: ADR 0005). Aparecen en P3 aunque no tengan precio,
# con estado "sin dato", para que se vea qué falta en vez de ocultarlo. Cambia esta lista si cambia el negocio.
INSUMOS_ESPERADOS = {
    "pastor": ["pastor", "tortilla", "cebolla", "cilantro", "limon", "pina"],
    "suadero": ["suadero", "tortilla", "cebolla", "cilantro", "limon"],
}

ESQUEMA_COSTO = pa.schema([
    ("anio", pa.int32()), ("semana_iso", pa.int32()), ("semana_inicio", pa.date32()), ("tipo_taco", pa.string()),
    ("costo_taco_mxn", pa.decimal128(8, 2)), ("indice_base100", pa.decimal128(8, 2)), ("semana_base", pa.date32()),
    ("incluye_merma", pa.bool_()), ("insumos_con_dato", pa.int32())])
ESQUEMA_PRECIO_INSUMO = pa.schema([
    ("anio", pa.int32()), ("semana_iso", pa.int32()), ("insumo", pa.string()), ("fuente", pa.string()),
    ("precio_kg", pa.decimal128(10, 2)), ("n_observaciones", pa.int32()), ("estadistico", pa.string())])
ESQUEMA_INFLACION = pa.schema([
    ("anio", pa.int32()), ("mes", pa.int32()), ("tipo_taco", pa.string()),
    ("indice_taco_base100", pa.decimal128(8, 2)), ("inpc_general_base100", pa.decimal128(8, 2)),
    ("inpc_alimentos_base100", pa.decimal128(8, 2)), ("inpc_pecuarios_base100", pa.decimal128(8, 2)),
    ("base_mes", pa.date32()), ("brecha_pp", pa.decimal128(8, 2))])
ESQUEMA_CONTRIBUCION = pa.schema([
    ("trimestre", pa.string()), ("tipo_taco", pa.string()), ("insumo", pa.string()),
    ("aportacion_mxn", pa.decimal128(8, 2)), ("aportacion_pct", pa.decimal128(8, 2)), ("ranking", pa.int32()), ("estado", pa.string())])
TABLAS = {"costo_taco_semanal": ESQUEMA_COSTO, "precio_insumo_semanal": ESQUEMA_PRECIO_INSUMO,
          "comparativo_inflacion": ESQUEMA_INFLACION, "contribucion_insumo": ESQUEMA_CONTRIBUCION}


def _q(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _lunes(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _trimestre(lunes: date) -> str:
    j = lunes + timedelta(days=3)
    return f"{j.year}Q{(j.month - 1) // 3 + 1}"


def _mes_de(lunes: date) -> tuple[int, int]:
    j = lunes + timedelta(days=3)  # el jueves decide a qué mes pertenece la semana (convención ISO)
    return j.year, j.month


def _precios_semanales(precios: pa.Table):
    """(lista de lunes, {(producto, lunes): (último precio vigente al cierre de la semana, n de avisos esa semana)})."""
    eventos: dict[str, list] = {}
    for f in sorted(precios.to_pylist(), key=lambda f: f["fecha_hora"]):
        if f["unidad"] == "kg":
            eventos.setdefault(f["producto"], []).append((f["fecha_hora"].date(), f["precio_unitario"]))
    if not eventos:
        return [], {}
    primera = _lunes(min(e[0][0] for e in eventos.values()))
    ultima = _lunes(max(e[-1][0] for e in eventos.values()))
    semanas = [primera + timedelta(weeks=i) for i in range((ultima - primera).days // 7 + 1)]
    por_semana: dict[tuple[str, date], tuple[Decimal, int]] = {}
    for producto, evs in eventos.items():
        vigente, i = None, 0
        for lunes in semanas:
            n = 0
            while i < len(evs) and evs[i][0] < lunes + timedelta(days=7):
                vigente, i, n = evs[i][1], i + 1, n + 1
            if vigente is not None:
                por_semana[(producto, lunes)] = (vigente, n)
    return semanas, por_semana


def calcular_gold(precios: pa.Table, receta: pa.Table, inpc: pa.Table | None, semana_base: date | None = None,
                  merma_pastor: Decimal = MERMA_PASTOR) -> dict[str, pa.Table]:
    semanas, por_semana = _precios_semanales(precios)

    filas_insumo = []
    for (producto, lunes), (precio, n) in sorted(por_semana.items()):
        iso = lunes.isocalendar()
        filas_insumo.append({"anio": iso.year, "semana_iso": iso.week, "insumo": producto, "fuente": "proveedor",
                             "precio_kg": _q(precio), "n_observaciones": n, "estadistico": "ultimo_vigente"})

    recetas: dict[str, list[tuple[str, int]]] = {}
    for r in receta.to_pylist():
        recetas.setdefault(r["tipo_taco"], []).append((r["insumo"], r["gramos_por_taco"]))

    filas_costo, indices = [], {}  # indices[(tipo_taco, lunes)] = índice sin redondear (versión base, sin merma)
    base_de: dict[str, date | None] = {}
    for tipo, lineas in sorted(recetas.items()):
        for con_merma in ([False, True] if tipo == "pastor" else [False]):
            semanas_tipo = []
            for lunes in semanas:
                costo, con_dato = Decimal(0), 0
                for insumo, gramos in lineas:
                    p = por_semana.get((insumo, lunes))
                    if p is None:
                        continue
                    linea = Decimal(gramos) / Decimal(1000) * p[0]
                    if con_merma and insumo == "pastor":
                        linea = linea / (1 - merma_pastor)
                    costo, con_dato = costo + linea, con_dato + 1
                if con_dato:
                    semanas_tipo.append((lunes, costo, con_dato))
            completas = [(l, c) for l, c, n in semanas_tipo if n == len(lineas)]
            base = semana_base or (completas[0][0] if completas else None)
            costo_base = next((c for l, c in completas if l == base), None)
            if not con_merma:
                base_de[tipo] = base if costo_base is not None else None
            for lunes, costo, con_dato in semanas_tipo:
                indice = None
                if costo_base is not None and con_dato == len(lineas) and lunes >= base:
                    indice = costo / costo_base * 100
                    if not con_merma:
                        indices[(tipo, lunes)] = indice
                iso = lunes.isocalendar()
                filas_costo.append({
                    "anio": iso.year, "semana_iso": iso.week, "semana_inicio": lunes, "tipo_taco": tipo,
                    "costo_taco_mxn": _q(costo), "indice_base100": _q(indice) if indice is not None else None,
                    "semana_base": base if costo_base is not None else None, "incluye_merma": con_merma,
                    "insumos_con_dato": con_dato})

    inpc_mes: dict[str, dict[tuple[int, int], Decimal]] = {}  # serie -> {(año, mes): índice}
    if inpc is not None:
        for f in inpc.to_pylist():
            inpc_mes.setdefault(f["serie_id"], {})[(f["fecha"].year, f["fecha"].month)] = f["indice"]

    def rebase(serie, anio, mes, mes_base):
        """Índice de la serie con base 100 en el mismo mes que el índice del taco; None si falta la serie o alguno de los dos meses."""
        v = inpc_mes.get(serie, {})
        return v[(anio, mes)] / v[mes_base] * 100 if (anio, mes) in v and mes_base in v else None
    filas_inflacion = []
    for tipo in sorted(recetas):
        base = base_de.get(tipo)
        if base is None:
            continue
        por_mes: dict[tuple[int, int], list[Decimal]] = {}
        for (t, lunes), idx in sorted(indices.items()):
            if t == tipo:
                por_mes.setdefault(_mes_de(lunes), []).append(idx)
        media = {m: sum(v) / len(v) for m, v in por_mes.items()}
        mes_base = _mes_de(base)
        for (anio, mes), m in sorted(media.items()):
            indice = m / media[mes_base] * 100
            inpc_idx = rebase(SERIE_GENERAL, anio, mes, mes_base)
            alimentos, pecuarios = rebase(SERIE_ALIMENTOS, anio, mes, mes_base), rebase(SERIE_PECUARIOS, anio, mes, mes_base)
            filas_inflacion.append({
                "anio": anio, "mes": mes, "tipo_taco": tipo, "indice_taco_base100": _q(indice),
                "inpc_general_base100": _q(inpc_idx) if inpc_idx is not None else None,
                "inpc_alimentos_base100": _q(alimentos) if alimentos is not None else None,
                "inpc_pecuarios_base100": _q(pecuarios) if pecuarios is not None else None,
                "base_mes": date(*mes_base, 1), "brecha_pp": _q(indice - inpc_idx) if inpc_idx is not None else None})

    filas_contribucion = _contribucion_por_insumo(semanas, por_semana, recetas)

    return {"costo_taco_semanal": pa.Table.from_pylist(filas_costo, schema=ESQUEMA_COSTO),
            "precio_insumo_semanal": pa.Table.from_pylist(filas_insumo, schema=ESQUEMA_PRECIO_INSUMO),
            "comparativo_inflacion": pa.Table.from_pylist(filas_inflacion, schema=ESQUEMA_INFLACION),
            "contribucion_insumo": pa.Table.from_pylist(filas_contribucion, schema=ESQUEMA_CONTRIBUCION)}


def _contribucion_por_insumo(semanas, por_semana, recetas) -> list[dict]:
    """P3: cuánto del cambio de costo por taco en cada trimestre explica cada insumo (primera vs. última semana con dato).
    Los insumos esperados que no tienen precio salen con estado "sin dato"; si el costo no cambió, "sin cambio"."""
    por_trimestre: dict[str, list[date]] = {}
    for lunes in semanas:
        por_trimestre.setdefault(_trimestre(lunes), []).append(lunes)
    filas = []
    for tipo, lineas in sorted(recetas.items()):
        gramos = dict(lineas)
        insumos = list(gramos) + [i for i in INSUMOS_ESPERADOS.get(tipo, []) if i not in gramos]
        for trimestre, sem in sorted(por_trimestre.items()):
            if len(sem) < 2:
                continue
            inicio, fin = sem[0], sem[-1]
            aporte: dict[str, Decimal] = {}
            for insumo in insumos:
                a, b = por_semana.get((insumo, inicio)), por_semana.get((insumo, fin))
                if insumo in gramos and a and b:
                    aporte[insumo] = Decimal(gramos[insumo]) / Decimal(1000) * (b[0] - a[0])
            total = sum(aporte.values(), Decimal(0))
            con_dato = [i for i in insumos if i in aporte]
            if total != 0:
                con_dato.sort(key=lambda i: aporte[i] / total, reverse=True)  # mayor parte del cambio primero
            sin_dato = [i for i in insumos if i not in aporte]
            for rango, insumo in enumerate(con_dato + sin_dato, start=1):
                con = insumo in aporte
                filas.append({
                    "trimestre": trimestre, "tipo_taco": tipo, "insumo": insumo,
                    "aportacion_mxn": _q(aporte[insumo]) if con else None,
                    "aportacion_pct": _q(aporte[insumo] / total * 100) if con and total != 0 else None,
                    "ranking": rango, "estado": ("ok" if total != 0 else "sin cambio") if con else "sin dato"})
    return filas
