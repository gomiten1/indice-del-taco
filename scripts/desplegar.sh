#!/usr/bin/env bash
# scripts/desplegar.sh
#
# Despliega todos los stacks del Indice del Taco en el orden correcto, en
# un solo comando y de forma idempotente. Reemplaza los pasos sueltos de
# infra/README.md. Cumple B1 del ROADMAP y habilita B2 (destruir -> desplegar).
#
# Uso minimo (desde la raiz del repo):
#   ./scripts/desplegar.sh --alert-email tu-correo@dominio.com
#
# Variables opcionales (sobrescriben los defaults):
#   PROJECT_NAME       default: indice-del-taco
#   ENVIRONMENT        default: dev
#   AWS_REGION         default: us-east-2       (ADR 0010)
#   BANXICO_TOKEN      se lee de ../.env si no viene en el entorno
#   DRY_RUN            si vale 1, imprime los comandos sin ejecutarlos
#
# Requiere: aws CLI v2, python3, acceso a la cuenta AWS del proyecto,
# y las plantillas de infra/ sin modificar sus nombres.

set -euo pipefail

# -------------------------------------------------------------------- flags

ALERT_EMAIL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --alert-email)   ALERT_EMAIL="${2:-}"; shift 2 ;;
    --project)       PROJECT_NAME="${2:-}"; shift 2 ;;
    --environment)   ENVIRONMENT="${2:-}"; shift 2 ;;
    --region)        AWS_REGION="${2:-}"; shift 2 ;;
    --dry-run)       DRY_RUN=1; shift ;;
    -h|--help)
      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "flag desconocido: $1" >&2; exit 2 ;;
  esac
done

: "${PROJECT_NAME:=indice-del-taco}"
: "${ENVIRONMENT:=dev}"
: "${AWS_REGION:=us-east-2}"
: "${DRY_RUN:=0}"

# -------------------------------------------------------------------- utilidades

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_DIR="$REPO_ROOT/infra"

say()  { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }
ok()   { printf "    \033[1;32mOK\033[0m %s\n" "$*"; }
run()  {
  if [[ "$DRY_RUN" = "1" ]]; then
    printf "    [dry] %s\n" "$*"
  else
    eval "$@"
  fi
}

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "falta la herramienta: $1" >&2; exit 1; }
}

# -------------------------------------------------------------------- chequeos previos

require aws
require python3

say "Verificando identidad y region"
CALLER="$(aws sts get-caller-identity --output json)"
ACCOUNT_ID="$(printf '%s' "$CALLER" | python3 -c 'import json,sys; print(json.load(sys.stdin)["Account"])')"
CURRENT_REGION="$(aws configure get region || echo "")"
if [[ -z "$CURRENT_REGION" ]]; then
  export AWS_DEFAULT_REGION="$AWS_REGION"
  CURRENT_REGION="$AWS_REGION"
fi
if [[ "$CURRENT_REGION" != "$AWS_REGION" ]]; then
  echo "region del perfil ($CURRENT_REGION) distinta a la esperada ($AWS_REGION); exporto AWS_DEFAULT_REGION=$AWS_REGION"
  export AWS_DEFAULT_REGION="$AWS_REGION"
fi
ok "cuenta $ACCOUNT_ID, region $AWS_REGION"

# Cargar token de Banxico desde .env si no viene del entorno
if [[ -z "${BANXICO_TOKEN:-}" ]]; then
  for env_file in "$REPO_ROOT/.env" "$REPO_ROOT/../.env"; do
    if [[ -f "$env_file" ]]; then
      # shellcheck disable=SC1090
      set -a; . "$env_file"; set +a
      break
    fi
  done
fi
if [[ -z "${BANXICO_TOKEN:-}" ]]; then
  echo "BANXICO_TOKEN no esta en el entorno ni en .env; abortando." >&2
  exit 1
fi
ok "BANXICO_TOKEN cargado (longitud=${#BANXICO_TOKEN})"

if [[ -z "$ALERT_EMAIL" ]]; then
  echo "falta --alert-email <correo> (destino de las alertas SNS)" >&2
  exit 2
fi

cd "$INFRA_DIR"
PARAM_COMMON="ProjectName=$PROJECT_NAME Environment=$ENVIRONMENT"
ART_BUCKET="$PROJECT_NAME-$ENVIRONMENT-artefactos-$ACCOUNT_ID"

# -------------------------------------------------------------------- 1. buckets del data lake

say "1/7  Bucket bronze (01-s3-bucket.yaml)"
run aws cloudformation deploy \
  --template-file 01-s3-bucket.yaml \
  --stack-name "$PROJECT_NAME-bronze" \
  --parameter-overrides "$PARAM_COMMON"

say "2/7  Silver + gold + cuarentena (03-s3-silver-gold-cuarentena.yaml)"
run aws cloudformation deploy \
  --template-file 03-s3-silver-gold-cuarentena.yaml \
  --stack-name "$PROJECT_NAME-lake" \
  --parameter-overrides "$PARAM_COMMON"

say "3/7  Bucket de artefactos para los .zip de las Lambdas (00-artefactos.yaml)"
run aws cloudformation deploy \
  --template-file 00-artefactos.yaml \
  --stack-name "$PROJECT_NAME-artefactos" \
  --parameter-overrides "$PARAM_COMMON"

# -------------------------------------------------------------------- 2. token en SSM

say "4/7  Token de Banxico en Parameter Store (SecureString)"
run aws ssm put-parameter \
  --name "/$PROJECT_NAME/$ENVIRONMENT/banxico_token" \
  --type SecureString \
  --value "'$BANXICO_TOKEN'" \
  --overwrite

# -------------------------------------------------------------------- 3. empaquetar y subir Lambdas

package_and_upload() {
  local name="$1"
  say "   Empaquetando $name"
  run python3 empaquetar_lambda.py "$name"
  local hash key
  if [[ "$DRY_RUN" = "1" ]]; then
    key="lambdas/${name}-DRYHASH.zip"
  else
    hash="$(python3 -c "import hashlib,sys;print(hashlib.sha256(open('build/${name}.zip','rb').read()).hexdigest()[:8])")"
    key="lambdas/${name}-${hash}.zip"
    run aws s3 cp "build/${name}.zip" "s3://$ART_BUCKET/$key"
  fi
  echo "$key"
}

say "5/7  Lambda de ingesta Banxico (04-lambda-ingesta-banxico.yaml)"
BANXICO_KEY="$(package_and_upload banxico)"
run aws cloudformation deploy \
  --template-file 04-lambda-ingesta-banxico.yaml \
  --stack-name "$PROJECT_NAME-banxico" \
  --parameter-overrides "$PARAM_COMMON" "CodeBucket=$ART_BUCKET" "CodeKey=$BANXICO_KEY" \
  --capabilities CAPABILITY_NAMED_IAM

say "6/7  Pipeline silver + gold (05-lambdas-silver-gold.yaml) y Glue + Athena (06-glue-athena.yaml)"
PIPELINE_KEY="$(package_and_upload pipeline)"
run aws cloudformation deploy \
  --template-file 05-lambdas-silver-gold.yaml \
  --stack-name "$PROJECT_NAME-pipeline" \
  --parameter-overrides "$PARAM_COMMON" "CodeBucket=$ART_BUCKET" "CodeKey=$PIPELINE_KEY" \
  --capabilities CAPABILITY_NAMED_IAM
run aws cloudformation deploy \
  --template-file 06-glue-athena.yaml \
  --stack-name "$PROJECT_NAME-athena" \
  --parameter-overrides "$PARAM_COMMON"

# -------------------------------------------------------------------- 4. orquestacion + alertas

say "7/7  Orquestacion y alertas (07-orquestacion-alertas.yaml)"
run aws cloudformation deploy \
  --template-file 07-orquestacion-alertas.yaml \
  --stack-name "$PROJECT_NAME-orquestacion" \
  --parameter-overrides "$PARAM_COMMON" "AlertEmail=$ALERT_EMAIL" \
    "CodeBucket=$ART_BUCKET" "CodeKey=$PIPELINE_KEY" \
  --capabilities CAPABILITY_NAMED_IAM

say "Todo desplegado"
echo
echo "   Siguiente paso: revisa tu correo ($ALERT_EMAIL) y confirma la suscripcion SNS."
echo "   Para ver el schedule:  aws scheduler list-schedules --query 'Schedules[].Name'"
echo "   Para corrida manual:   aws lambda invoke --function-name $PROJECT_NAME-$ENVIRONMENT-orquestador --payload '{}' --cli-binary-format raw-in-base64-out out.json"
