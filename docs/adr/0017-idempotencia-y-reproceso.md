# ADR 0017: Idempotencia y reproceso

**Estado:** Aceptada provisionalmente
**Fecha:** 2026-11-18

## Contexto

N6 exige que volver a procesar una semana no duplique registros ni cambie el histórico, y que cualquier semana se pueda recalcular desde los datos originales.

## Decisión

- **Bronze:** la llave lleva la `fecha_ingesta` (`raw/<fuente>/.../fecha_ingesta=AAAA-MM-DD/`). La ingesta de Banxico compara el ETag (MD5) y **no reescribe** si el contenido no cambió.
- **Silver:** cada tabla se **reemplaza completa** desde su archivo de origen: se escribe un archivo `datos.parquet` fijo por partición (`anio`, `semana_iso`) y se **borran las particiones obsoletas**. La cuarentena se escribe siempre, aunque quede vacía, para que no sobreviva una cuarentena vieja.
- **Gold:** cada tabla se reescribe completa a partir de silver.
- El chat se procesa **entero** en cada corrida (el cálculo de cambios relativos depende del historial).

## Razón

Reemplazar es más simple y más seguro que hacer upserts: el resultado depende solo de los datos de entrada. Verificado el 2026-11-16: dos corridas de Banxico, silver y gold dejan los mismos archivos, y gold en AWS es idéntico al cálculo local.

## Consecuencias

- El `ejecucion_id` dentro de los archivos de cuarentena cambia en cada corrida; el contenido de los datos, no.
- Los buckets están versionados: las versiones anteriores se conservan 30 días.
- Falta la prueba explícita de "recalcular una semana desde bronze" (roadmap 3.6).
