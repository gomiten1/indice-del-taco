# ADR 0004: Infraestructura como Código con AWS CloudFormation modular

* **Estado:** Aceptado
* **Fecha:** 2026-11-16
* **Autores:** Equipo Data Solutions — La TaquerIA Opus

## Contexto
El proyecto requiere reproducibilidad total en una cuenta nueva de AWS sin configurar recursos manualmente en la consola, manteniendo separación de ciclos de vida entre el almacenamiento persistente y el cómputo efímero.

## Decisión
1. Definir toda la infraestructura mediante plantillas declarativas en **AWS CloudFormation** dentro de `infra/` (`00-artefactos.yaml` a `07-orquestacion-alertas.yaml`), validables localmente con `cfn-lint`.
2. Separar los stacks de almacenamiento (`indice-taco-bronze`, `indice-taco-lake`) con `DeletionPolicy: Retain` y `UpdateReplacePolicy: Retain` de los stacks de cómputo y orquestación (`indice-taco-banxico`, `indice-taco-pipeline`, `indice-taco-athena`, `indice-taco-orquestacion`).
3. Asignar un rol IAM de mínimo privilegio independiente por cada función Lambda, restringido únicamente a los prefijos S3 y parámetros SSM necesarios.

## Consecuencias
* **Positivas:** Los stacks de cómputo pueden destruirse y recrearse sin riesgo de pérdida de datos históricos; despliegue auditable y parametrizado por entorno (`dev` / `prod`).
* **Negativas:** Obliga a respetar el orden de despliegue entre stacks que exportan e importan valores (`Fn::ImportValue`).