# ADR 0003: Estadístico del precio semanal

**Estado:** Aceptada provisionalmente (pendiente de revisión del equipo)
**Fecha:** 2026-11-16

## Contexto

Cada semana hay muchos precios públicos por insumo (PROFECO trae cientos de miles de filas por quincena, con precios extremos y duplicados) y hay que resumirlos en uno solo para calcular el costo del taco y compararlo con el proveedor. El SOW deja abierto si usar media, mediana o media recortada.

## Decisión

El precio de un insumo en una semana ISO es la **mediana** del `precio_kg` de las observaciones de CDMX de esa semana, por canal (menudeo y mayoreo por separado). Si una semana no tiene observaciones se muestra **"sin dato"**: no se interpola ni se inventa. El proveedor no necesita estadístico: se usa su último precio vigente al domingo 23:59 (aclaración A6).

## Razón

- La mediana no se mueve por un precio absurdo (por ejemplo, un error de captura en una tienda); la media sí, y la media recortada necesita elegir un porcentaje de recorte.
- Es fácil de explicar a una persona no técnica ("el precio de en medio").
- Con pocas observaciones (la Central de Abasto tiene 1 a 22 filas por insumo) la mediana sigue funcionando, y se guarda `n_observaciones` para que se vea cuán sólida es.

## Consecuencias

- `precio_insumo_semanal.estadistico` vale `mediana` y se guarda `n_observaciones`.
- Quedan semanas sin dato cuando PROFECO tiene huecos; el dashboard lo dice.
- Si el equipo prefiere otra, se cambia en un solo lugar del cálculo gold y se actualiza este ADR.
