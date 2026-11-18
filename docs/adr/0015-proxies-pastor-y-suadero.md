# ADR 0015: Proxies de PROFECO para pastor y suadero

**Estado:** Aceptada provisionalmente (**pendiente de aprobación de la dueña**, SOW §8)
**Fecha:** 2026-11-18

## Contexto

PROFECO no trae "pastor" ni "suadero", así que la comparación contra el mercado (P2) y la contribución por insumo (P3) necesitan un corte equivalente. `fuentes.md` documenta una muestra de CDMX de `b07_2026_q2.csv` (julio, segunda quincena).

## Decisión

| Insumo | Proxy en PROFECO | Referencia observada |
| :---- | :---- | :---- |
| Pastor | Pierna de cerdo sin hueso o pernil | mediana ≈ $108/kg (115 registros) |
| Suadero | Cortes de res como falda | mediana ≈ $231/kg |
| Mayoreo | Filas de Central de Abasto CDMX (`giro = Central de Abasto`) | 1,289 filas, 136 productos en esa quincena |

Toda comparación contra estos proxies se marca como **aproximada**. Si falta el dato de una semana se muestra "sin dato" ([ADR 0019](0019-datos-faltantes-sin-dato.md)).

## Razón

Es lo más parecido disponible en una fuente oficial; SNIIM, la alternativa, no ofrece descarga ni API ([ADR 0011](0011-ingesta-hibrida-profeco-sniim.md)).

## Consecuencias

- **Implementado el 18/11** ([ADR 0020](0020-profeco-csv-y-cobertura.md), [0021](0021-reglas-silver-profeco.md), [0022](0022-p2-mercado-unidades-y-diagnostico.md)): P2 tiene datos en las semanas 29 a 31 de 2026. Medianas reales: pastor $108/kg, suadero $231/kg.
- La muestra de mayoreo es pequeña (tortilla 2 filas, cilantro 1); la comparación puede ser poco robusta.
- La dueña debe aprobar las equivalencias.
