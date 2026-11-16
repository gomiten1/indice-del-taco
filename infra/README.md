# infra/ — Plantillas de CloudFormation

Base de infraestructura en AWS para el pipeline del Índice del Taco.
Son las plantillas iniciales entregadas en clase: la capa bronze (bucket S3)
y una Lambda de ejemplo que escribe ahí. Más adelante se extienden con el
código real de ingesta (Banxico, PROFECO, INEGI) y las capas silver / gold.

## Archivos

| Archivo | Qué crea |
|---|---|
| `00-artefactos.yaml` | Bucket para los `.zip` de las Lambdas, separado del data lake. |
| `01-s3-bucket.yaml` | Bucket S3 de la capa bronze: versionado, cifrado (AES‑256), acceso público bloqueado, ciclo de vida que borra versiones antiguas a los 30 días, `DeletionPolicy: Retain` (no se borra con el stack). Exporta `BronzeBucketName` y `BronzeBucketArn`. |
| `02-lambda.yaml` | Lambda `python3.13` con rol IAM de mínimo privilegio (solo `s3:PutObject` bajo `raw/` del bucket bronze), LogGroup explícito con 14 días de retención y un `handler` de demostración. Importa `BronzeBucketArn` y `BronzeBucketName` del stack del bucket. |
| `03-s3-silver-gold-cuarentena.yaml` | Tres buckets (silver, gold, cuarentena) con las mismas prácticas que bronze. Exporta nombre y ARN de cada uno. |
| `04-lambda-ingesta-banxico.yaml` | Lambda `python3.13` que descarga el INPC de Banxico a `raw/banxico/` de bronze. Rol con solo `s3:PutObject` en ese prefijo y `ssm:GetParameter` sobre su token. Código en `src/ingesta/banxico.py`. |

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

## Desplegar silver/gold y la ingesta de Banxico

Región: la de tu perfil (`us-east-2`, ver [ADR 0010](../docs/adr/0010-cuenta-aws-y-region.md)). Validar sin AWS: `.venv/bin/cfn-lint infra/*.yaml`.

Orden (cada stack importa del anterior). Los stacks **ya están desplegados** en la cuenta del proyecto; esto sirve para recrearlos.

```bash
P="ProjectName=indice-del-taco Environment=dev"
aws cloudformation deploy --template-file 01-s3-bucket.yaml              --stack-name indice-taco-bronze     --parameter-overrides $P
aws cloudformation deploy --template-file 03-s3-silver-gold-cuarentena.yaml --stack-name indice-taco-lake     --parameter-overrides $P
aws cloudformation deploy --template-file 00-artefactos.yaml             --stack-name indice-taco-artefactos --parameter-overrides $P

# Token de Banxico en Parameter Store (se lee de .env; no se imprime ni se guarda en el repo)
set -a; source ../.env; set +a
aws ssm put-parameter --name /indice-del-taco/dev/banxico_token --type SecureString --value "$BANXICO_TOKEN"

# Empaquetar el codigo, subirlo al bucket de artefactos y desplegar la Lambda
python empaquetar_lambda.py banxico
aws s3 cp build/banxico.zip s3://indice-del-taco-dev-artefactos-<ID-DE-CUENTA>/lambdas/banxico.zip
aws cloudformation deploy --template-file 04-lambda-ingesta-banxico.yaml --stack-name indice-taco-banxico \
  --parameter-overrides $P CodeBucket=indice-del-taco-dev-artefactos-<ID-DE-CUENTA> --capabilities CAPABILITY_NAMED_IAM

# Probarla dos veces: la segunda escribe en las mismas llaves (el bucket versionado conserva la version anterior 30 dias)
aws lambda invoke --function-name indice-del-taco-dev-ingesta-banxico --payload '{"fecha_ingesta":"2026-11-16"}' --cli-binary-format raw-in-base64-out out.json
```

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
