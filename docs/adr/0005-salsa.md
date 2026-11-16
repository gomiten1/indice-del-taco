# ADR 0005: Tratamiento de la salsa en el costo del taco

**Estado:** Aceptada provisionalmente (pendiente de revisión del equipo)
**Fecha:** 2026-11-16

## Contexto

La receta del taco incluye salsa, pero la dueña no ha dicho si la salsa se prepara en el local o se compra, ni cuánto cuesta por taco (aclaraciones, pregunta 3). No hay precio de compra ni cantidad por taco, y PROFECO no tiene un equivalente claro.

## Decisión

La salsa **no entra al costo del taco** por ahora. Se declara como supuesto en el dashboard y en el diccionario de datos, y `costo_taco_semanal.insumos_con_dato` muestra cuántos insumos de la receta sí se contaron.

## Razón

- Cualquier costo que pusiéramos sería inventado, y el SOW prohíbe inventar datos (§8).
- Excluirla subestima el nivel del costo, pero **casi no afecta al índice** (que es relativo y base 100) si el costo de la salsa se mueve poco frente a la carne.
- Es reversible: al llegar el dato, se agrega una fila a `silver_receta` y gold la recoge sin cambiar código.

## Consecuencias

- El costo en pesos por taco se presenta como "costo de insumos considerados", no como costo total.
- Se mantiene abierta la aclaración (pregunta 3); si la dueña responde, se actualiza este ADR.
