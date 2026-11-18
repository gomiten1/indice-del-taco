# ADR 0018: La inflación sale de Banxico (INEGI queda como limitación)

**Estado:** Aceptada provisionalmente (**cambia el alcance del SOW**: requiere aprobación escrita de la dueña, SOW §11)
**Fecha:** 2026-11-18

## Contexto

El SOW incluye INEGI y Banxico y N4 pide comparar contra la inflación **general y de alimentos**. De INEGI el token funciona y el tema del INPC es `0137`, pero **no se encontró el ID del indicador** (se probaron más de 15 candidatos). La serie de alimentos tampoco se ha localizado.

## Decisión

- La inflación general es el **INPC de Banxico (`SP1`)**: fuente única por ahora. INEGI no se implementa.
- ~~`inpc_alimentos_base100` queda vacío hasta encontrar la serie.~~ **Actualización 18/11:** la serie se encontró en el catálogo del SIE (ver `docs/fuentes.md`). Se usará **`SP66540` (Alimentos, Bebidas y Tabaco)** y, como segunda línea, **`SP56386` (Pecuarios)**, ambas por la API de Banxico y no por INEGI. Mientras no se implemente, la columna sigue vacía ([ADR 0019](0019-datos-faltantes-sin-dato.md)).
- Aclaración para el dashboard: «Alimentos, Bebidas y Tabaco» es del índice **subyacente** (productos procesados; no incluye frutas, verduras ni carne fresca) y «Pecuarios» es **no subyacente** (más volátil). Ninguna es «toda la comida».

## Razón

Banxico ya cubre P4 con el INPC general, es una API estable y está probada (694 observaciones, 1969–2026). Seguir buscando el ID de INEGI no bloquea nada. La serie de alimentos tampoco necesita INEGI: está en el SIE.

## Consecuencias

- N4 quedará cubierto por completo cuando se implementen `SP66540` y `SP56386` (pendiente).
- El catálogo de INEGI (3.9 MB) está en `bronze_local/` por si se retoma la búsqueda.
