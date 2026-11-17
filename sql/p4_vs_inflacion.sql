-- P4: ¿Mi costo sube más o menos que la inflación?
-- Índice del taco (mensual, base 100 en el mes base) contra el INPC general con la misma base.
-- brecha_pp > 0 significa que el taco subió más que la inflación (en puntos porcentuales).
SELECT anio, mes, tipo_taco, indice_taco_base100, inpc_general_base100, brecha_pp
FROM comparativo_inflacion
WHERE tipo_taco = 'pastor'
ORDER BY anio, mes;
