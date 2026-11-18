# ADR 0019: Datos faltantes se muestran como "sin dato", nunca como cero

**Estado:** Aceptada provisionalmente
**Fecha:** 2026-11-18

## Contexto

El SOW (§8) prohíbe inventar precios y pide marcar "sin dato" o "último dato disponible". En la práctica faltan cosas: P2 no tiene mercado, P3 no tiene precios de tortilla, cebolla, cilantro, limón ni piña, y no hay inflación de alimentos. Un snapshot anterior mostraba esos insumos con "aporte 0.0 %", que parece un dato y no lo es.

## Decisión

- Lo que no tiene dato va **vacío (nulo)** en gold y se muestra como **"Sin dato"** o **"Aún sin datos"** en el dashboard.
- P3 lista los insumos esperados del taco aunque no tengan precio, con `estado = 'sin dato'`, para que se vea qué falta; un costo que no cambió sale `sin cambio`, no 0 %.
- El índice no se calcula si falta algún insumo de la receta (ADR 0009); P2 vacío muestra "Aún sin datos".
- Un mes sin INPC deja la comparación vacía pero conserva el índice del taco.

## Razón

Un cero afirma algo que no se sabe y puede llevar a una mala decisión de precios. Mostrar la ausencia es más honesto y se ve qué dato falta conseguir.

## Consecuencias

- Hoy P2 está vacío y P3 solo tiene la carne con valor.
- Las listas de insumos esperados (`INSUMOS_ESPERADOS`) viven en el código de gold; cambiar de negocio implica editarlas.
