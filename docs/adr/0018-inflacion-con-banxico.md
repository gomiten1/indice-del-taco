# ADR 0018: La inflación sale de Banxico (INEGI queda como limitación)

**Estado:** Aceptada provisionalmente (**cambia el alcance del SOW**: requiere aprobación escrita de la dueña, SOW §11)
**Fecha:** 2026-11-18

## Contexto

El SOW incluye INEGI y Banxico y N4 pide comparar contra la inflación **general y de alimentos**. De INEGI el token funciona y el tema del INPC es `0137`, pero **no se encontró el ID del indicador** (se probaron más de 15 candidatos). La serie de alimentos tampoco se ha localizado.

## Decisión

- La inflación general es el **INPC de Banxico (`SP1`)**: fuente única por ahora. INEGI no se implementa.
- `inpc_alimentos_base100` queda **vacío** (sin dato) hasta encontrar la serie ([ADR 0019](0019-datos-faltantes-sin-dato.md)).

## Razón

Banxico ya cubre P4 con el INPC general, es una API estable y está probada (694 observaciones, 1969–2026). Seguir buscando el ID de INEGI no bloquea nada.

## Consecuencias

- N4 queda cubierto solo en parte (falta inflación de alimentos): limitación a documentar.
- El catálogo de INEGI (3.9 MB) está en `bronze_local/` por si se retoma la búsqueda.
