# ADR 0022: P2 con PROFECO: precio por kilo o por manojo y diagnóstico de ±10 %

**Estado:** Aceptada provisionalmente. **Abierto:** el umbral de ±10 % lo propuso el equipo; la dueña debe confirmarlo (pregunta 7 de `docs/consultoria/aclaraciones.md`)
**Fecha:** 2026-11-18

## Contexto

Con el CSV real ([ADR 0020](0020-profeco-csv-y-cobertura.md)) hay precios de mercado para tres semanas de julio. El cilantro viene por manojo y no se puede pasar a kilo sin inventar un peso.

## Decisión

- **El precio de mercado se guarda tal como viene:** `precio_insumo_semanal` tiene `precio` y `unidad` (`kg` o `manojo`); sustituye a `precio_kg`. El cilantro queda en **manojo** (mediana ≈ $10), sin conversión.
- **Estadístico:** mediana semanal por insumo y canal ([ADR 0003](0003-estadistico-precio-semanal.md)); `n_observaciones` dice cuántos avisos la respaldan.
- **P2 (`comparativo_proveedor`)** compara el precio del proveedor contra el menudeo y el mayoreo **solo kilo contra kilo** y solo en las semanas con dato de mercado. Un manojo nunca se compara con un kilo.
- **Diagnóstico:** brecha contra el **menudeo**: más de +10 % = «caro», menos de −10 % = «barato», entre ambos «en rango». Sin menudeo, «sin dato».
- **`aproximado`** es verdadero cuando el insumo usa un proxy ([ADR 0015](0015-proxies-pastor-y-suadero.md)): pastor y suadero.
- `precio_proveedor_kg` es privado y **no** sale en el snapshot público ([ADR 0012](0012-privacidad-precios-proveedor.md)).

## Consecuencias

- P3 con más insumos **no** depende del mercado sino de la receta: hoy solo trae gramos de pastor y suadero; tortilla, cebolla, limón, piña y cilantro siguen «sin dato» hasta tener sus gramos por taco (dato de la dueña).
- Como el cilantro va por manojo, para entrar al costo por taco se necesitará su gramaje por taco **y** el peso de un manojo.
- Con datos sintéticos el pastor sale «caro» (+42 % contra una pierna sin hueso) y el suadero «barato» (−25 %); son resultados de prueba, no de la taquería.
