# ADR 0008: Tratamiento de la merma

**Estado:** Aceptada provisionalmente (pendiente de revisión del equipo)
**Fecha:** 2026-11-16

## Contexto

Del trompo de pastor sobran 6 a 7 kg diarios de unos 55 kg comprados (≈12%), que se consumen como cena del personal y no están en la receta (aclaraciones A3 y A5). Es un costo real de la carne. No hay un dato equivalente para el suadero.

## Decisión

- **Índice base:** usa la receta tal cual (55 g de suadero, 50 g de pastor), **sin merma**.
- **Sensibilidad:** se calcula además una versión con merma solo para el **pastor**, dividiendo el costo de la carne entre (1 − 0.12). El 12% es un parámetro configurable (`MERMA_PASTOR`). El suadero no se ajusta por falta de dato.
- Ambas versiones se guardan en `costo_taco_semanal`, diferenciadas por `incluye_merma`.

## Razón

- El índice base debe ser comparable con la receta de la dueña y fácil de explicar; mezclar merma ahí lo haría depender de un dato incierto.
- Mostrar la sensibilidad responde a la duda de la dueña sin esconder el supuesto.

## Consecuencias

- El dashboard presenta el índice base y, aparte, el efecto de la merma en el pastor.
- Si la dueña confirma la cifra (A5), se actualiza el parámetro y este ADR.
