# ADR 0014: Frecuencia por fuente y manejo del rezago

**Estado:** Aceptada provisionalmente
**Fecha:** 2026-11-18

## Contexto

Las fuentes no llegan igual (pendiente en `fuentes.md`): Banxico publica el INPC cada mes pero se consulta cada semana; PROFECO publica por quincena y se carga a mano; el chat del proveedor es una exportación manual que no se sube cada semana; la receta casi no cambia. Si silver exigiera todas las fuentes con la fecha de la corrida, fallaría cada lunes.

## Decisión

- La corrida semanal usa, **por fuente, el archivo más reciente de bronze con `fecha_ingesta` menor o igual a la fecha de la corrida**.
- Las fechas usadas se devuelven en `fechas_origen` y quedan en `registro_ejecuciones`.
- Si el **chat o Banxico** llevan más de **10 días** de rezago, se envía una alerta (regla de completitud por fuente del SOW). La **receta** queda exenta.
- Si no existe ningún archivo anterior o igual, la etapa **falla** (no se inventa).

## Razón

No fallar por una fuente que no cambia, pero tampoco usar datos viejos sin avisar. El umbral de 10 días deja pasar una semana sin chat nuevo y avisa a la segunda.

## Consecuencias

- El primer lunes sin chat nuevo no alerta; el segundo sí (ocurrirá el 30/11 con los datos sintéticos).
- El número 10 es provisional (`UMBRAL_REZAGO_DIAS`, ver [ADR 0016](0016-reglas-y-umbrales-de-calidad.md)).
