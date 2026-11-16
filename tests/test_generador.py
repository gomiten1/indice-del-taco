"""Pruebas del generador sintético (E1: misma semilla, mismos datos)."""
from datetime import date
from decimal import Decimal

from datos_sinteticos.generador import generar_chat, generar_receta, generar_ventas
from ingesta.parser_chat import parsear_chat


def test_misma_semilla_mismos_datos():
    assert generar_chat(semilla=7) == generar_chat(semilla=7)
    assert generar_ventas(semilla=7) == generar_ventas(semilla=7)


def test_otra_semilla_otros_datos():
    assert generar_chat(semilla=1) != generar_chat(semilla=2)


def test_un_mensaje_de_precios_por_jueves_de_enero_a_septiembre():
    chat = generar_chat(semilla=42, errores=False)
    fechas = {p.fecha.date() for p in parsear_chat(chat).precios}
    assert min(fechas) == date(2026, 1, 1) and max(fechas) == date(2026, 9, 24)
    assert all(f.weekday() == 3 for f in fechas)  # jueves


def test_horario_de_don_beto_entre_6_48_y_7_15():
    for p in parsear_chat(generar_chat(semilla=42, errores=False)).precios:
        assert (6, 48) <= (p.fecha.hour, p.fecha.minute) <= (7, 15)


def test_serie_sigue_las_aclaraciones():
    """A1: suadero 165 a 185, pastor 138 a 155, longaniza 110 a 118 (primera y última semana)."""
    precios = parsear_chat(generar_chat(semilla=42, errores=False)).precios
    for producto, inicio, fin in [("suadero", 165, 185), ("pastor", 138, 155), ("longaniza", 110, 118)]:
        serie = sorted((p.fecha, p.precio) for p in precios if p.producto == producto)
        assert serie[0][1] == Decimal(inicio) and serie[-1][1] == Decimal(fin)


def test_sin_errores_el_parser_no_rechaza_nada():
    assert parsear_chat(generar_chat(semilla=42, errores=False)).rechazos == []


def test_con_errores_hay_cuarentena_de_cada_tipo():
    motivos = {r.motivo for r in parsear_chat(generar_chat(semilla=42, errores=True)).rechazos}
    assert {"precio_invalido", "unidad_desconocida", "fecha_invalida"} <= motivos


def test_los_errores_no_cambian_la_serie_de_precios():
    """Los errores son extras: la serie final (con correcciones aplicadas) es la misma que sin errores."""
    def serie(errores):
        ps = parsear_chat(generar_chat(semilla=42, errores=errores)).precios
        return sorted((p.fecha.date(), p.producto, p.precio) for p in ps)
    assert serie(True) == serie(False)


def test_receta_toma_las_cantidades_de_las_aclaraciones():
    receta = {fila["producto"]: fila["gramos_por_taco"] for fila in generar_receta()}
    assert receta == {"suadero": 55, "pastor": 50}


def test_ventas_diarias_entre_200_y_400_tacos():
    ventas = generar_ventas(semilla=42)
    assert len(ventas) == 273  # 1 ene a 30 sep 2026
    assert all(200 <= v["tacos"] <= 400 for v in ventas)
