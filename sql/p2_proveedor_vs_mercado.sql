-- P2: ¿el proveedor cobra caro o barato frente al mercado CDMX (PROFECO)?
-- Solo hay filas en las semanas con datos de mercado (hoy 2026 S29 a S31; ver registro_ejecuciones, fuente = 'profeco').
-- brecha = (proveedor / mercado - 1) x 100. diagnostico: caro > +10 %, barato < -10 % contra el menudeo.
-- aproximado = true: pastor y suadero se comparan con un corte parecido (pierna de cerdo sin hueso; falda de res).
SELECT anio, semana_iso, insumo, precio_proveedor_kg, precio_menudeo_kg, precio_mayoreo_kg,
       brecha_menudeo_pct, brecha_mayoreo_pct, aproximado, diagnostico
FROM comparativo_proveedor
ORDER BY insumo, anio, semana_iso;
