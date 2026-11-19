# infra/ — Plantillas de CloudFormation

Plantillas de CloudFormation de todo el pipeline del Índice del Taco, numeradas en el orden en que se despliegan: buckets,
Lambdas de ingesta, silver y gold, catálogo de Glue y Athena, y la orquestación con alertas. La región es la de la cuenta (ver
[ADR 0010](../docs/adr/0010-cuenta-aws-y-region.md)).

## Archivos

| Archivo | Qué crea |
|---|---|
| `00-artefactos.yaml` | Bucket para los `.zip` de las Lambdas, separado del data lake. |
| `01-s3-bucket.yaml` | Bucket S3 de la capa bronze: versionado, cifrado (AES‑256), acceso público bloqueado, ciclo de vida que borra versiones antiguas a los 30 días, `DeletionPolicy: Retain` (no se borra con el stack). Exporta `BronzeBucketName` y `BronzeBucketArn`. |
| `03-s3-silver-gold-cuarentena.yaml` | Tres buckets (silver, gold, cuarentena) con las mismas prácticas que bronze. Exporta nombre y ARN de cada uno. |
| `04-lambda-ingesta-banxico.yaml` | Lambda `python3.13` que descarga las series del INPC de Banxico (`SP1`, `SP66540` y `SP56386`, parámetro `BanxicoSeries`) a `raw/banxico/` de bronze. Rol con solo `s3:PutObject` en ese prefijo y `ssm:GetParameter` sobre su token. Código en `src/ingesta/banxico.py`. |
| `05-lambdas-silver-gold.yaml` | Lambdas de silver y gold (un paquete, dos handlers) con roles de mínimo privilegio por bucket y la capa de pandas. |
| `06-glue-athena.yaml` | Base de datos y tablas de Glue (DDL manual, partition projection), workgroup de Athena con tope de bytes y bucket de resultados. |
| `07-orquestacion-alertas.yaml` | Lambda orquestadora, EventBridge Scheduler (lunes 6:00 CDMX), tema SNS con suscripción por correo y dos alarmas de CloudWatch. |

## Orden de despliegue

Cada stack importa valores que exporta el anterior (`Fn::ImportValue`); si se invierte el orden, el despliegue falla con
`Export … cannot be found`. El orden es `01` → `03` → `00` → token → `04` → `05` → `06` → `07`, y se detalla en las secciones siguientes.
El flag `--capabilities CAPABILITY_NAMED_IAM` es necesario en las plantillas que crean roles con nombre (`04`, `05` y `07`).

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

### Silver, gold y Athena (stacks `indice-taco-pipeline` e `indice-taco-athena`)

```bash
python empaquetar_lambda.py pipeline                       # imprime la llave sugerida, p. ej. lambdas/pipeline-25f8aec0.zip
aws s3 cp build/pipeline.zip s3://indice-del-taco-dev-artefactos-<ID-DE-CUENTA>/lambdas/pipeline-<hash>.zip
aws cloudformation deploy --template-file 05-lambdas-silver-gold.yaml --stack-name indice-taco-pipeline \
  --parameter-overrides $P CodeBucket=indice-del-taco-dev-artefactos-<ID-DE-CUENTA> CodeKey=lambdas/pipeline-<hash>.zip \
  --capabilities CAPABILITY_NAMED_IAM
aws cloudformation deploy --template-file 06-glue-athena.yaml --stack-name indice-taco-athena --parameter-overrides $P

# Datos de entrada en bronze (sinteticos) y ejecucion
aws s3 cp ../data/sintetico/chat_proveedor.txt "s3://<bronze>/raw/chat/fecha_ingesta=AAAA-MM-DD/chat_proveedor.txt"
aws s3 cp ../data/sintetico/receta.csv        "s3://<bronze>/raw/interno/fecha_ingesta=AAAA-MM-DD/receta.csv"
aws lambda invoke --function-name indice-del-taco-dev-silver --payload '{"fecha_ingesta":"AAAA-MM-DD"}' --cli-binary-format raw-in-base64-out out.json
aws lambda invoke --function-name indice-del-taco-dev-gold   --payload '{}' --cli-binary-format raw-in-base64-out out.json
```

La capa de pandas (`PandasLayerArn`) es la administrada AWS SDK for pandas para Python 3.13 y depende de la region (version 17 en `us-east-2`).
Las consultas estan en `sql/` y se ejecutan en el workgroup `indice-del-taco-dev` (tope de 100 MB por consulta).

### Orquestación y alertas (stack `indice-taco-orquestacion`)

```bash
# AlertEmail NO va en el repo: se pasa al desplegar. SNS manda un correo de confirmacion que hay que aceptar.
aws cloudformation deploy --template-file 07-orquestacion-alertas.yaml --stack-name indice-taco-orquestacion \
  --parameter-overrides $P AlertEmail=<tu-correo> CodeBucket=indice-del-taco-dev-artefactos-<ID-DE-CUENTA> CodeKey=lambdas/pipeline-<hash>.zip \
  --capabilities CAPABILITY_NAMED_IAM

# Corrida manual y falla simulada (etapa: ingesta, silver o gold) para probar que el correo llega
aws lambda invoke --function-name indice-del-taco-dev-orquestador --payload '{}' --cli-binary-format raw-in-base64-out out.json
aws lambda invoke --function-name indice-del-taco-dev-orquestador --payload '{"simular_falla":"silver"}' --cli-binary-format raw-in-base64-out out.json
```

EventBridge Scheduler corre el orquestador **cada lunes a las 6:00 (hora de CDMX)**. Alertas: el orquestador avisa en cuanto una
etapa falla o silver reporta datos sospechosos/atrasados; una alarma avisa si el orquestador mismo se cae, y otra si pasan 7 dias
sin ejecutarse. Cada corrida queda en la tabla `registro_ejecuciones` (consultable en Athena).

## Parámetros

| Parámetro | Tipo | Valor típico | Validación |
|---|---|---|---|
| `ProjectName` | String | `indice-del-taco` | `^[a-z0-9-]{3,30}$` |
| `Environment` | String | `dev` | `dev` o `prod` |

## Despliegue en un solo comando

Desde la raíz del repo, con la sesión de AWS activa (o `aws configure`) y `BANXICO_TOKEN` en el entorno o en `.env`:

```bash
./scripts/desplegar.sh --alert-email tu-correo@dominio.com
```

El script valida identidad y región, carga el token, despliega los 7 stacks en orden idempotente y empaqueta/sube las Lambdas. Flags: `--project`, `--environment`, `--region`, `--dry-run`.

## Despliegue automático desde GitHub (CD)

El workflow [`.github/workflows/cd.yml`](../.github/workflows/cd.yml) corre el mismo `scripts/desplegar.sh` cada vez que hay push a `main` con cambios en `infra/`, `src/`, el script o el workflow (también se puede disparar manualmente desde la pestaña *Actions* del repo).

OIDC está bloqueado en la cuenta AWS del proyecto, así que el workflow usa Access Key del usuario IAM `indice-taco-dev` (política `AdministratorAccess`), leída desde Secrets del repo:

| Secret | Qué guarda |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access Key ID del usuario IAM `indice-taco-dev` |
| `AWS_SECRET_ACCESS_KEY` | Secret Access Key correspondiente |
| `AWS_REGION` | `us-east-2` |
| `ALERT_EMAIL` | Destinatario principal de las alertas SNS (se puede sobrescribir con un input al disparar el workflow a mano) |
| `BANXICO_TOKEN` | *Opcional*. Si se provee, se refresca el parámetro en SSM en cada despliegue. Si no, el script omite ese paso asumiendo que ya existe de un despliegue previo. |

Para rotar la Access Key: crear una **Clave de acceso 2** desde IAM, actualizar los dos Secrets, verificar un despliegue exitoso y **desactivar** la clave vieja (no borrar inmediatamente, por si hay rollback).

## Pendiente

- Prueba destruir → desplegar completa (roadmap B2); `scripts/desplegar.sh` deja la mitad reproducible.
- El **Budget** de AWS existe pero se creó a mano; no está en ninguna plantilla.
- La ingesta de **PROFECO** (carga manual a bronze, [ADR 0011](../docs/adr/0011-ingesta-hibrida-profeco-sniim.md)).

## Notas

- Los tags `project` y `environment` sirven para desglosar la factura en Cost Explorer (hay que activarlos como etiquetas de costos
  en Billing; ver `docs/costos.md`).
- `DeletionPolicy: Retain` y `UpdateReplacePolicy: Retain` en los buckets protegen los datos ante un `cloudformation delete`
  accidental: para eliminar todo hay que vaciar los buckets a mano.
- La plantilla demo de la primera versión (`02-lambda.yaml`, una Lambda con código en línea) se eliminó: la reemplazó la Lambda real de Banxico (`04`).
