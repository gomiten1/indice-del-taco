# ADR 0007: Reconstrucción de los datos internos sintéticos

**Estado:** Propuesta
**Fecha:** 2026-11-16

## Contexto

El SOW (§2, E1) pide un generador de datos sintéticos reproducible que "tome como semilla el extracto del chat del brief", y un parser que resuelva los casos del "Anexo A del brief". Este ADR funciona como el supuesto del mismo. Sin él no hay chat de ejemplo ni lista oficial de casos, pero el generador y el parser son lo primero que bloquea al resto del pipeline (silver, gold, índice).

## Decisión

Reconstruimos el extracto y los casos a partir de lo que **sí** está documentado en el repo, y lo que no, lo declaramos como supuesto. Si aparece el brief, se compara y se corrige este ADR.

### Hechos tomados de los documentos del repo (no inventados)

| Hecho | Fuente |
| :---- | :---- |
| Periodo del histórico: enero a septiembre de 2026 | SOW §4 |
| Suadero pasa de $165 a $185 por kilo (≈12.1%); pastor de $138 a $155 (≈12.3%); longaniza de $110 a $118 (≈7.3%) | `aclaraciones.md` A1 |
| El extracto tiene 8 mensajes de Don Beto, todos en jueves entre las 6:48 y las 7:15 de la mañana | `aclaraciones.md` A6 |
| Receta: 55 g de suadero y 50 g de pastor por taco | `aclaraciones.md` A2 |
| Casos que debe resolver el parser: precios con y sin `$`, unidades implícitas, cambios relativos, correcciones, productos que "siguen igual" ("lo demás igual"), mensajes sin precios | SOW §2 y E1 |
| Errores intencionales para probar la cuarentena: precios en cero, fechas inválidas, unidades desconocidas | SOW §2 |
| El archivo es un `.txt` exportado de WhatsApp; no hay conexión en vivo | ADR 0001 |

### Supuestos propios (inventados, a validar)

| Supuesto | Razón |
| :---- | :---- |
| Formato de exportación estilo Android en español de México: `d/m/aa, h:mm a. m. - Remitente: mensaje`; un mensaje puede ocupar varias líneas | Es el formato más común del `.txt`; el parser tolera ambos extremos de la línea de fecha y se amplía si hace falta |
| Remitentes: `Don Beto` (proveedor) y `Ofelia` (dueña) | Nombres que aparecen en el RFP y las aclaraciones |
| Redacción exacta de cada mensaje, cantidades de cambios relativos ("subió 5 pesos") y correcciones ("perdón, el pastor es 150") | El brief no está; se escriben de modo que cada caso aparezca en al menos un mensaje |
| El chat sintético sigue la serie de precios de las aclaraciones, interpolada de forma semanal con ruido controlado por la semilla | Para que el índice tenga movimiento y coincida con los totales observados |
| Ventas diarias: se generan solo como dato de apoyo; no entran al índice | SOW §8: las ventas no son indispensables para el costo unitario |

### Catálogo de casos del parser

Cada caso tiene al menos una prueba unitaria y aparece en el chat sintético:

| # | Caso | Ejemplo | Resultado esperado |
| :---- | :---- | :---- | :---- |
| C1 | Precio con `$` | `pastor $155 el kilo` | pastor, 155.00, kg |
| C2 | Precio sin `$` | `suadero 185` | suadero, 185.00, kg (unidad implícita) |
| C3 | Unidad implícita | `longaniza 118` | longaniza, 118.00, kg |
| C4 | Cambio relativo | `el pastor subió 5 pesos` | requiere el precio anterior vigente |
| C5 | Corrección | `perdón, el pastor es 150` | reemplaza el último precio del mismo producto |
| C6 | "Lo demás igual" | `lo demás sigue igual` | repite el precio vigente de los productos no mencionados |
| C7 | Mensaje sin precios | `buenos días, ya llegó el pedido` | se ignora, no es error |
| C8 | Mensaje de la dueña | cualquier mensaje de `Ofelia` | no es precio de proveedor, se ignora |
| C9 | Precio en cero o negativo | `pastor $0` | rechazo a cuarentena |
| C10 | Unidad desconocida | `suadero 185 la caja` | rechazo a cuarentena, alerta |
| C11 | Fecha inválida | `31/2/26, 6:50 a. m. - ...` | rechazo a cuarentena |

## Consecuencias

- Todo lo derivado de este ADR (formato, textos, números) es **sintético y se identifica como tal** en el dashboard y la documentación, como pide el SOW §8.
- Cada hecho de la tabla "tomados de los documentos" se conserva; los supuestos se pueden cambiar sin tocar el parser si la redacción cambia, porque el parser se prueba contra el catálogo de casos, no contra un archivo fijo.
- Si el brief aparece y difiere, se actualiza este ADR y se cambian las pruebas afectadas.
- Pendiente de validar con la dueña: aclaraciones A1 y A6 (porcentaje de aumento y día en que llegan los precios), porque determinan el aspecto real del chat.
