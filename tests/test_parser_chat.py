"""Pruebas del parser del chat de WhatsApp. Un caso del ADR 0007 por prueba (C1 a C11)."""
from datetime import datetime
from decimal import Decimal

from ingesta.parser_chat import parsear_chat


def msg(dia, texto, hora="6:52 a. m.", remitente="Don Beto"):
    return f"{dia}, {hora} - {remitente}: {texto}"


def un_precio(texto):
    r = parsear_chat(texto)
    assert not r.rechazos, r.rechazos
    return r.precios


# --- C1 a C3: precios simples ---------------------------------------------

def test_c1_precio_con_signo_de_pesos():
    [p] = un_precio(msg("15/1/26", "pastor $155 el kilo"))
    assert (p.producto, p.precio, p.unidad) == ("pastor", Decimal("155.00"), "kg")
    assert p.fecha == datetime(2026, 1, 15, 6, 52)


def test_c2_precio_sin_signo_de_pesos():
    [p] = un_precio(msg("15/1/26", "suadero 185"))
    assert (p.producto, p.precio, p.unidad) == ("suadero", Decimal("185.00"), "kg")


def test_c3_unidad_implicita_es_kilo():
    [p] = un_precio(msg("15/1/26", "Longaniza 118"))
    assert (p.producto, p.precio, p.unidad) == ("longaniza", Decimal("118.00"), "kg")


def test_varios_productos_en_un_mensaje():
    ps = un_precio(msg("15/1/26", "Buen día. Pastor $155, suadero 185 y longaniza 118 el kilo"))
    assert {(p.producto, p.precio) for p in ps} == {
        ("pastor", Decimal("155.00")), ("suadero", Decimal("185.00")), ("longaniza", Decimal("118.00"))}


def test_unidad_pieza_explicita():
    [p] = un_precio(msg("15/1/26", "longaniza 12 la pieza"))
    assert p.unidad == "pieza"


def test_decimal_con_coma():
    [p] = un_precio(msg("15/1/26", "pastor $155,50 el kilo"))
    assert p.precio == Decimal("155.50")


def test_hora_pm_y_formato_con_espacio_no_separable():
    [p] = un_precio("15/1/26, 1:05 p. m. - Don Beto: pastor 155")
    assert p.fecha == datetime(2026, 1, 15, 13, 5)


def test_mensaje_multilinea():
    chat = "15/1/26, 6:52 a. m. - Don Beto: Buenos días\npastor $155\nsuadero 185"
    ps = un_precio(chat)
    assert {p.producto for p in ps} == {"pastor", "suadero"}


# --- C4: cambio relativo --------------------------------------------------

def test_c4_cambio_relativo_sube_en_pesos():
    chat = "\n".join([msg("15/1/26", "pastor $150"), msg("22/1/26", "el pastor subió 5 pesos")])
    ps = un_precio(chat)
    assert [p.precio for p in ps] == [Decimal("150.00"), Decimal("155.00")]
    assert ps[1].tipo == "relativo"


def test_c4_cambio_relativo_baja_y_porcentaje():
    chat = "\n".join([msg("15/1/26", "suadero 200"), msg("22/1/26", "suadero bajó 10 pesos"),
                      msg("29/1/26", "suadero subió 10%")])
    assert [p.precio for p in un_precio(chat)] == [Decimal("200.00"), Decimal("190.00"), Decimal("209.00")]


def test_c4_subio_a_es_precio_absoluto():
    chat = "\n".join([msg("15/1/26", "pastor 150"), msg("22/1/26", "pastor subió a 160")])
    assert un_precio(chat)[1].precio == Decimal("160.00")


def test_c4_relativo_sin_precio_previo_va_a_cuarentena():
    r = parsear_chat(msg("15/1/26", "el pastor subió 5 pesos"))
    assert r.precios == []
    assert [x.motivo for x in r.rechazos] == ["cambio_relativo_sin_base"]


# --- C5: corrección -------------------------------------------------------

def test_c5_correccion_reemplaza_el_ultimo_precio():
    chat = "\n".join([msg("15/1/26", "pastor $1550"), msg("15/1/26", "perdón, el pastor es 155", hora="6:58 a. m.")])
    ps = un_precio(chat)
    assert [(p.producto, p.precio, p.tipo) for p in ps] == [("pastor", Decimal("155.00"), "correccion")]
    assert ps[0].fecha == datetime(2026, 1, 15, 6, 52)  # vigente desde el aviso original


def test_c5_correccion_sin_precio_previo_se_toma_como_precio():
    [p] = un_precio(msg("15/1/26", "perdón, el pastor es 150"))
    assert p.precio == Decimal("150.00")


# --- C6: "lo demás igual" -------------------------------------------------

def test_c6_lo_demas_igual_repite_precios_vigentes():
    chat = "\n".join([msg("15/1/26", "pastor 150, suadero 180, longaniza 110"),
                      msg("22/1/26", "pastor $155, lo demás igual")])
    ps = [p for p in un_precio(chat) if p.fecha.day == 22]
    assert {(p.producto, p.precio, p.tipo) for p in ps} == {
        ("pastor", Decimal("155.00"), "explicito"),
        ("suadero", Decimal("180.00"), "repetido"),
        ("longaniza", Decimal("110.00"), "repetido")}


def test_c6_lo_demas_igual_sin_historia_no_inventa_precios():
    r = parsear_chat(msg("15/1/26", "pastor 150, lo demás sigue igual"))
    assert [p.producto for p in r.precios] == ["pastor"]


# --- C7 y C8: mensajes que se ignoran -------------------------------------

def test_c7_mensaje_sin_precios_se_ignora():
    r = parsear_chat(msg("15/1/26", "buenos días, ya llegó el pedido de pastor"))
    assert r.precios == [] and r.rechazos == []


def test_c8_mensajes_de_la_duena_se_ignoran():
    r = parsear_chat(msg("15/1/26", "ok, pastor 150 entonces", remitente="Ofelia"))
    assert r.precios == [] and r.rechazos == []


def test_lineas_de_sistema_se_ignoran():
    r = parsear_chat("15/1/26, 6:00 a. m. - Los mensajes y las llamadas están cifrados de extremo a extremo.")
    assert r.precios == [] and r.rechazos == []


# --- C9 a C11: cuarentena -------------------------------------------------

def test_c9_precio_cero_va_a_cuarentena():
    r = parsear_chat(msg("15/1/26", "pastor $0"))
    assert r.precios == [] and [x.motivo for x in r.rechazos] == ["precio_invalido"]


def test_c9_precio_cero_no_actualiza_el_precio_vigente():
    chat = "\n".join([msg("15/1/26", "pastor 150"), msg("22/1/26", "pastor $0"), msg("29/1/26", "pastor subió 5 pesos")])
    assert [p.precio for p in parsear_chat(chat).precios] == [Decimal("150.00"), Decimal("155.00")]


def test_c10_unidad_desconocida_va_a_cuarentena():
    r = parsear_chat(msg("15/1/26", "suadero 185 la caja"))
    assert r.precios == [] and [x.motivo for x in r.rechazos] == ["unidad_desconocida"]
    assert "caja" in r.rechazos[0].detalle


def test_c11_fecha_invalida_va_a_cuarentena():
    r = parsear_chat(msg("31/2/26", "pastor 150"))
    assert r.precios == [] and [x.motivo for x in r.rechazos] == ["fecha_invalida"]
    assert r.rechazos[0].linea == 1


def test_c11_fecha_invalida_sin_precios_no_es_error():
    assert parsear_chat(msg("31/2/26", "buenos días")).rechazos == []


def test_un_rechazo_no_tumba_el_resto_del_chat():
    chat = "\n".join([msg("15/1/26", "pastor $0"), msg("22/1/26", "pastor 150")])
    r = parsear_chat(chat)
    assert len(r.precios) == 1 and len(r.rechazos) == 1


def test_mismo_chat_mismo_resultado():
    chat = "\n".join([msg("15/1/26", "pastor 150"), msg("22/1/26", "pastor subió 5 pesos")])
    assert parsear_chat(chat) == parsear_chat(chat)
