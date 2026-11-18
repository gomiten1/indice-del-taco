# ADR 0013: Orquestación con EventBridge Scheduler y una Lambda orquestadora

**Estado:** Aceptada provisionalmente
**Fecha:** 2026-11-18

## Contexto

El README original decía que silver y gold se disparaban con eventos de S3; el SOW decía EventBridge Scheduler. Las opciones eran: (a) eventos de S3 encadenados por capa, (b) Step Functions, (c) una Lambda que invoque las etapas en orden.

## Decisión

**(c)**. EventBridge Scheduler dispara cada **lunes a las 6:00 (America/Mexico_City)** la Lambda `orquestador`, que invoca en orden `ingesta-banxico → silver → gold`, escribe una fila por etapa y fuente en `registro_ejecuciones` y avisa por SNS (`infra/07`).

- Si una etapa **falla**: se registra, se avisa y se **detiene** (lo malo no se usa).
- Si silver reporta datos **sospechosos o atrasados**: se avisa y se sigue (lo malo ya quedó en cuarentena).
- El orquestador **no tiene reintentos automáticos** (`MaximumRetryAttempts: 0`) para no mandar correos repetidos; reprocesar es seguro porque todo es idempotente ([ADR 0017](0017-idempotencia-y-reproceso.md)).
- Dos alarmas de CloudWatch cubren lo que el propio orquestador no puede avisar: que falle él mismo y que pasen 7 días sin ejecutarse.

## Razón

- El orden queda garantizado y las fallas y alertas viven en un solo lugar.
- El SOW pide evitar Step Functions salvo que sean indispensables; aquí no lo son.
- Encadenar por eventos de S3 arriesga bucles y ejecuciones duplicadas (una Lambda que escribe donde otra escucha).

## Consecuencias

- El orquestador tiene un límite de 300 s; si el pipeline crece (PROFECO de 223 MB por quincena), habrá que pasar a Step Functions o separar etapas.
- El README y el diagrama debían corregirse (la arquitectura real no usa eventos de S3).
