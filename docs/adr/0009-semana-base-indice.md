# ADR 0009: Semana base del Índice del Taco

**Estado:** Aceptada provisionalmente (pendiente de revisión del equipo)
**Fecha:** 2026-11-16

## Contexto

El índice vale 100 en una semana base y todo lo demás se mide contra ella. La dueña no ha dicho desde cuándo quiere comparar (aclaraciones, pregunta 5). El histórico sintético empieza en enero de 2026, pero los datos públicos tienen huecos (en 2026 aparentan faltar febrero q1, marzo y abril).

## Decisión

La semana base es **la primera semana en que el costo del taco se puede calcular con todos los insumos de la receta que sí tienen dato** (proveedor y mercado). Se guarda en un parámetro configurable (`SEMANA_BASE`) y en la columna `semana_base` de `costo_taco_semanal`. Para comparar con la inflación mensual, el mes base es el mes de esa semana.

## Razón

- Una base con datos completos evita que el 100 se fije sobre un costo parcial y distorsione todo el índice.
- Parametrizarla permite cambiarla si la dueña pide otra fecha, sin tocar el código de cálculo.

## Consecuencias

- Las semanas anteriores a la base no tienen índice (se muestran como "sin base").
- Hay que documentar en el dashboard qué semana es la base.
- Si se responde la pregunta 5, se actualiza este ADR y el parámetro.
