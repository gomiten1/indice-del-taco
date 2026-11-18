# ADR 0012: Privacidad del snapshot público (riesgo aceptado)

**Estado:** Aceptada provisionalmente (pendiente de revisión del equipo)
**Fecha:** 2026-11-18

## Contexto

El RFP (§6) y el SOW (§8) piden que el tablero público no exponga los precios de compra exactos del proveedor. Al mismo tiempo, N1 exige mostrar el **costo por taco en pesos**, y el dashboard explica la receta (55 g de suadero, 50 g de pastor) para que la dueña lo entienda (N7).

Eso tiene un efecto: con la receta pública, **el precio del kilo se despeja** del costo por taco. Verificado el 2026-11-18 con el snapshot: pastor $6.90 / 0.05 kg = $138 (semana 1) y $155 (semana 39); suadero ≈ $165 y $185, que son los precios del chat. Con P2 pasaría algo parecido: la brecha porcentual contra el mercado más el precio de mercado (público) permiten recuperar el precio.

## Decisión

**Se acepta el riesgo y se documenta.** Se mantiene el costo en pesos (N1) y la receta visible (N7). Lo que sí se aplica:

- El snapshot **no incluye** la columna `precio_proveedor_kg` ni las filas de `precio_insumo_semanal` con `fuente = 'proveedor'` (lo hace `transformacion.snapshot`, con prueba).
- No se publican ventas, mensajes, nombre ni teléfono del proveedor.

## Razón

- Ocultar la receta o el costo en pesos contradice N1 y N7.
- Lo expuesto es un precio por kilo de carne, no ventas ni datos personales, y hoy los datos son sintéticos.
- El tablero con login se descartó en el [ADR 0001](0001-alcance.md) por salirse de la ingeniería de datos.

## Consecuencias

- Hay que revisarlo **antes de publicar con datos reales**. Mitigaciones disponibles: redondear el costo (por ejemplo a $0.50), mostrar solo el índice base 100, o publicar con retraso.
- El [ADR 0006](0006-dashboard-streamlit.md) ya no puede decir "confidencialidad estricta": protege las columnas, no el valor derivado.
