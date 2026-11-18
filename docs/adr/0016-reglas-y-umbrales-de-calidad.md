# ADR 0016: Reglas y umbrales de calidad

**Estado:** Aceptada provisionalmente (los valores son supuestos del equipo, no del cliente)
**Fecha:** 2026-11-18

## Contexto

El SOW lista las reglas de calidad y deja varios umbrales "por definir en H3". Sin valores concretos no se puede probar la cuarentena ni las alertas.

## Decisión

| Regla | Qué pasa | Valor |
| :---- | :---- | :---- |
| Precio mayor a cero | Cuarentena (`precio_invalido`) | — |
| Fecha válida y no futura | Cuarentena (`fecha_invalida`, `fecha_futura`) | — |
| Unidad reconocida | Cuarentena (`unidad_desconocida`, `unidad_no_soportada`); se aceptan `kg` y `pieza`, `paquete` se rechaza (no se puede convertir) | — |
| Cambio relativo sin precio previo | Cuarentena (`cambio_relativo_sin_base`) | — |
| Variación contra el precio anterior | Se **marca** `sospechoso`, **no se descarta** (puede ser real) | **> 25 %** |
| Proporción de registros en cuarentena | Alerta por correo | **> 10 %** |
| Fuente atrasada (chat, Banxico) | Alerta por correo ([ADR 0014](0014-frecuencia-y-rezago-por-fuente.md)) | **> 10 días** |
| Esquema inesperado | **Detiene el pipeline** y avisa (`EsquemaInesperado`) | — |

## Razón

Rechazar lo claramente inválido, marcar lo dudoso sin perder datos reales y detener todo cuando la forma del archivo cambia (no adivinar). Con los datos sintéticos, los cambios semanales normales son de pocos pesos (< 10 %), así que 25 % deja margen sin ocultar saltos grandes.

## Consecuencias

- Cada valor está en una constante (`UMBRAL_VARIACION`, `UMBRAL_CUARENTENA`, `UMBRAL_REZAGO_DIAS`) y se cambia en un solo lugar.
- Con datos reales habrá que recalibrarlos.
