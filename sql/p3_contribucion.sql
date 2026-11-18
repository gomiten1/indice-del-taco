-- P3: ¿Qué insumo explica el aumento de costos?
-- Contribución de cada insumo al cambio del costo por taco en el último trimestre con datos.
-- estado = 'sin dato' significa que todavía no hay precios de ese insumo (no que aporte 0 %): ADR 0019.
SELECT tipo_taco, ranking, insumo, aportacion_mxn, aportacion_pct, estado
FROM contribucion_insumo
WHERE trimestre = (SELECT max(trimestre) FROM contribucion_insumo)
ORDER BY tipo_taco, ranking;
