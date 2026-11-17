-- P1: ¿Cuánto cuesta hoy cada taco de suadero y de pastor?
-- Costo de la carne por taco en la última semana disponible (versión base, sin merma) y su índice base 100.
-- Base de datos: indice_taco_dev (Athena, workgroup indice-del-taco-dev).
WITH ult AS (
    SELECT tipo_taco, max(semana_inicio) AS semana_inicio
    FROM costo_taco_semanal
    WHERE NOT incluye_merma
    GROUP BY tipo_taco
)
SELECT c.tipo_taco, c.semana_inicio, c.costo_taco_mxn, c.indice_base100, c.insumos_con_dato
FROM costo_taco_semanal c
JOIN ult u ON c.tipo_taco = u.tipo_taco AND c.semana_inicio = u.semana_inicio
WHERE NOT c.incluye_merma
ORDER BY c.tipo_taco;
