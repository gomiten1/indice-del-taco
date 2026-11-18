-- P4: ¿Mi costo sube más o menos que la inflación?
-- Índice del taco (mensual, base 100 en el mes base) contra el INPC general, la inflación de alimentos y la de pecuarios,
-- todos con la misma base. brecha_pp > 0 significa que el taco subió más que el INPC general (en puntos porcentuales).
-- «Alimentos» (SP66540) es del índice subyacente: productos procesados, sin frutas, verduras ni carne fresca.
-- «Pecuarios» (SP56386) es no subyacente: más volátil. Ninguna es «toda la comida». Si falta una serie, la columna sale vacía (sin dato).
SELECT anio, mes, tipo_taco, indice_taco_base100, inpc_general_base100, inpc_alimentos_base100, inpc_pecuarios_base100, brecha_pp
FROM comparativo_inflacion
WHERE tipo_taco = 'pastor'
ORDER BY anio, mes;
