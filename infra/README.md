# infra/ — Plantillas de CloudFormation

Base de infraestructura en AWS para el pipeline del Índice del Taco.
Son las plantillas iniciales entregadas en clase: la capa bronze (bucket S3)
y una Lambda de ejemplo que escribe ahí. Más adelante se extienden con el
código real de ingesta (Banxico, PROFECO, INEGI) y las capas silver / gold.

## Archivos

| Archivo | Qué crea |
|---|---|
| `01-s3-bucket.yaml` | Bucket S3 de la capa bronze: versionado, cifrado (AES‑256), acceso público bloqueado, ciclo de vida que borra versiones antiguas a los 30 días, `DeletionPolicy: Retain` (no se borra con el stack). Exporta `BronzeBucketName` y `BronzeBucketArn`. |
| `02-lambda.yaml` | Lambda `python3.13` con rol IAM de mínimo privilegio (solo `s3:PutObject` bajo `raw/` del bucket bronze), LogGroup explícito con 14 días de retención y un `handler` de demostración. Importa `BronzeBucketArn` y `BronzeBucketName` del stack del bucket. |

## Orden de despliegue

Primero el bucket (porque exporta valores), luego la Lambda (porque los
importa). Si se invierte el orden, el segundo `deploy` falla con
`Export … cannot be found`.

```bash
aws cloudformation deploy \
  --template-file 01-s3-bucket.yaml \
  --stack-name indice-taco-bronze \
  --parameter-overrides ProjectName=indice-del-taco Environment=dev
```

```bash
aws cloudformation deploy \
  --template-file 02-lambda.yaml \
  --stack-name indice-taco-extract \
  --parameter-overrides ProjectName=indice-del-taco Environment=dev \
  --capabilities CAPABILITY_NAMED_IAM
```

El flag `--capabilities CAPABILITY_NAMED_IAM` es necesario porque la
plantilla de la Lambda crea un rol con `RoleName` explícito.

## Parámetros

| Parámetro | Tipo | Valor típico | Validación |
|---|---|---|---|
| `ProjectName` | String | `indice-del-taco` | `^[a-z0-9-]{3,30}$` |
| `Environment` | String | `dev` | `dev` o `prod` |

## Qué falta para que sea la ingesta real del proyecto

Estas plantillas son el cascarón. Para que corran la ingesta real hay que:

1. **Reemplazar el handler demo** por el código que llama Banxico SIE,
   CKAN de PROFECO e INEGI, y guarda cada respuesta tal cual bajo
   `raw/<fuente>/YYYY/MM/DD/`. El código vive en `src/` (pendiente de
   crear) y se empaqueta con `aws cloudformation package`.
2. **Mover los tokens a AWS Systems Manager Parameter Store**
   (`SecureString`), nunca al YAML ni al código. El rol de la Lambda
   necesita permiso `ssm:GetParameter` sobre esas rutas.
3. **Agregar un trigger:** `AWS::Scheduler::Schedule` (EventBridge
   Scheduler) con `cron` semanal — H5 del SOW.
4. **Crear los buckets de silver y gold** (otros dos stacks hermanos del
   01) y la Lambda de transformación con la capa administrada
   **AWS SDK for pandas**.
5. **Observabilidad:** alarmas de CloudWatch + tópico SNS + un
   AWS::Budgets con alerta a $250 MXN/mes — H0 y H6 del SOW.

## Notas

- El código Python está **inline** (`ZipFile: |`) solo porque es un
  ejercicio de clase. En el proyecto real pasa a `src/` y se empaqueta.
- Los tags `project` y `environment` se usan después para desglosar la
  factura en Cost Explorer (tema del `costos.md`).
- `DeletionPolicy: Retain` y `UpdateReplacePolicy: Retain` en el bucket
  blindan los datos ante un `cloudformation delete` accidental.
