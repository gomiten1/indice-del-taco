# Guía de réplica para otro negocio o sucursal

Cómo adaptar **El Índice del Taco** a otra taquería, sucursal o comercio de comida. Solo se tocan **tres cosas**: el nombre del proyecto, los datos del negocio y las alertas con su calendario. Los comandos exactos están en [`infra/README.md`](../infra/README.md); aquí está el orden y qué cambiar.

## Antes de empezar

* Una cuenta de AWS donde se puedan desplegar CloudFormation, S3, Lambda, Glue, Athena, EventBridge, SNS y Systems Manager. Los stacks se crean en **la región de la cuenta**.
* Un token gratuito de la API SIE de Banxico (INPC, serie `SP1`).
* La exportación del chat con el proveedor en texto (`.txt`) y la receta del negocio.
* Python 3.12 y el repositorio clonado (`pip install -r requirements-dev.txt` para correr pruebas y el empaquetado).

## 1. Nombre del proyecto y entorno

Los nombres de buckets, funciones y stacks salen de dos parámetros. Para otro negocio se cambia `ProjectName` (por ejemplo `indice-taco-sucursal-norte`, solo minúsculas, números y guiones) y `Environment` (`dev` o `prod`):

```bash
P="ProjectName=indice-taco-sucursal-norte Environment=prod"
```

El orden de despliegue es: `01` bronze → `03` silver/gold/cuarentena → `00` artefactos → token de Banxico en Parameter Store → `04` Lambda de Banxico → `05` silver y gold → `06` Glue y Athena → `07` orquestación. Cada stack importa valores del anterior; si se invierte el orden, falla con `Export ... cannot be found`.

La capa de pandas (`PandasLayerArn` en `05` y `07`) es un ARN **que depende de la región**: hay que buscar el de AWS SDK for pandas para Python 3.13 en la región de la cuenta.

## 2. Datos del negocio (sin tocar el código)

Se suben a bronze con la fecha del día (`fecha_ingesta=AAAA-MM-DD`):

| Archivo | Dónde va | Qué contiene |
| :---- | :---- | :---- |
| `receta.csv` | `raw/interno/fecha_ingesta=.../receta.csv` | Columnas `producto,gramos_por_taco` (hoy: `suadero,55` y `pastor,50`) |
| `chat_proveedor.txt` | `raw/chat/fecha_ingesta=.../chat_proveedor.txt` | Exportación de WhatsApp del proveedor con los precios |

Con eso cambian los costos y el índice. El chat se sube cuando hay precios nuevos; si pasan más de 10 días sin chat nuevo, llega una alerta (ADR 0014).

## 3. Alertas y calendario

Se pasan al desplegar `07`:

* `AlertEmail`: el correo que recibe las alertas (SNS manda un correo de confirmación que hay que aceptar; sin eso no llega nada).
* `ScheduleExpression`: por defecto `cron(0 6 ? * MON *)`, lunes 6:00 hora de CDMX. Se cambia el día y la hora según el negocio.
* El token de Banxico va en Parameter Store como `SecureString` (`/<proyecto>/<entorno>/banxico_token`), nunca en el repositorio.

## Qué sí requiere tocar el código (limitaciones conocidas)

La meta de N8 es cambiar solo receta y precios, pero hoy dos listas están en el código:

1. **Productos que reconoce el parser del chat:** `PRODUCTOS` en `src/ingesta/parser_chat.py` (hoy pastor, suadero y longaniza). Un negocio con otros productos debe agregarlos ahí.
2. **Insumos esperados de cada platillo** para P3: `INSUMOS_ESPERADOS` en `src/transformacion/gold.py`.

También quedan fuera de la réplica automática: la carga de PROFECO (manual, ADR 0011) y la serie de inflación de alimentos (pendiente).

## Verificar que funciona

1. Correr el orquestador a mano (`aws lambda invoke ... indice-...-orquestador`) y mirar la tabla `registro_ejecuciones` (consultas en `docs/runbook.md`).
2. Consultar P1 y P4 con los archivos de `sql/` en Athena.
3. Regenerar el snapshot del dashboard: `PYTHONPATH=.:src python -m transformacion.snapshot --bucket <bucket-gold>` y publicar `dashboard/app.py` en Streamlit Community Cloud.
4. Probar las alertas con la falla simulada (sección 7 del runbook).
