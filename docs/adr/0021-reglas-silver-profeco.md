# ADR 0021: Reglas del silver de PROFECO (unidades, calidad y duplicados)

**Estado:** Aceptada
**Fecha:** 2026-11-18

## Contexto

Con el archivo real se vio que: no trae «pastor» ni «suadero», muchos productos comparten nombre con presentaciones distintas (pieza, lata, manojo, kilo), y el mismo aviso aparece repetido
(346 de 1,839 combinaciones en las filas útiles; 6 con precios distintos).

## Decisión

- **Filtro:** solo `estado = Ciudad de México` y solo las equivalencias de [ADR 0015](0015-proxies-pastor-y-suadero.md) (pastor y suadero = proxy; longaniza, tortilla de maíz, cebolla blanca, limón, piña y cilantro = exacta).
  Se excluyen tortilla de harina, cebolla morada y cambray, piña en almíbar y cortes distintos a los del ADR.
- **Unidad:** `precio_kg` solo si la presentación viene en kilos; si no, `unidad = manojo` y se conserva el `precio` ([ADR 0022](0022-p2-mercado-unidades-y-diagnostico.md)). No se inventa un peso.
- **Canal:** `Central de Abasto` = mayoreo; el resto = menudeo.
- **Cuarentena:** precio no numérico o ≤ 0, y fecha inválida. Misma alerta que las demás fuentes (> 10 %).
- **Duplicados:** una fila por tienda, producto y día; si repiten con precios distintos, la **mediana**. Se cuenta cuántos se colapsaron (`duplicados`).
- **Esquema:** si faltan columnas esperadas, se detiene el pipeline (`EsquemaInesperado`), como en las otras fuentes.
- **Lectura por bloques** de 8 MB: el archivo no se carga entero en memoria.

## Consecuencias

- Silver reemplaza la tabla completa al escribir, por lo que `combinar` junta todos los archivos antes de escribir ([ADR 0017](0017-idempotencia-y-reproceso.md)).
- El cilantro se publica por manojo; para el costo del taco hará falta su gramaje y el peso de un manojo (aclaración a la dueña).
