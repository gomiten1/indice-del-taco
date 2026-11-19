# Control y Estimación de Costos en AWS — El Índice del Taco

> Las cifras de la sección 1 son **estimaciones**, no mediciones. El gasto real se mide en la sección 3 (pendiente).

* **Región de despliegue:** `us-east-2` (US East — Ohio)
* **Entorno:** `dev`
* **Presupuesto mensual objetivo (SOW):** ≤ $250.00 MXN/mes (~$12.50 USD)

---

## 1. Desglose estimado por servicio (Operación semanal)

Al operar bajo una arquitectura 100 % *serverless* sin servidores EC2, bases de datos RDS encendidas ni NAT Gateways, el costo mensual del pipeline se mantiene dentro de la capa gratuita y créditos educativos de AWS:

| Servicio AWS | Uso mensual estimado (4 corridas/mes) | Costo mensual estimado (USD) | Notas de optimización |
| :--- | :--- | :---: | :--- |
| **Amazon S3** (`bronze`, `silver`, `gold`, `quarantine`, `artefactos`, `athena-results`) | < 50 MB almacenados, < 500 solicitudes PUT/GET | $0.01 | Versionado con ciclo de vida que expira versiones no actuales a los 30 días (resultados de Athena: 7 días). |
| **AWS Lambda** (Ingesta Banxico, Silver, Gold, Orquestador) | ~20 invocaciones/mes, 512 MB RAM, < 10 s por ejecución | $0.00 | Cubierto íntegramente por el Free Tier permanente (1M de solicitudes/mes). |
| **Amazon Athena** | ~30 consultas analíticas/mes (< 1 KB escaneado por consulta) | $0.01 | Formato columnar Parquet + Partition Projection + tope estricto de **100 MB** por consulta en el Workgroup. |
| **AWS Glue Data Catalog** | 1 base de datos y < 10 tablas registradas | $0.00 | Sin Crawlers encendidos; DDL manual y Partition Projection. |
| **EventBridge Scheduler + CloudWatch + SNS** | 4 disparos cron/mes, logs con retención de 14 días, < 20 correos/mes | $0.00 | Retención explícita de 14 días en LogGroups para evitar acumulación histórica. |
| **Streamlit Community Cloud** (Dashboard público) | Hosting del tablero `dashboard/app.py` sobre `snapshot_gold/` | $0.00 | Capa gratuita comunitaria; desacoplado de AWS. |
| **TOTAL ESTIMADO MENSUAL** | | **~$0.02 USD (~$0.40 MXN)** | **99.8 % por debajo del tope de $250 MXN/mes.** |

---

## 2. Controles preventivos implementados

1. **Tope de escaneo en Athena (`100 MB`):** Configurado en `infra/06-glue-athena.yaml` (`BytesScannedCutoffPerQuery: 104857600`) para bloquear cualquier consulta mal formada antes de generar cargos.
2. **Etiquetado de recursos (`Tags`):** Todos los recursos creados por CloudFormation incluyen las etiquetas `project=indice-del-taco` y `environment=dev` para filtrar el gasto real en **AWS Cost Explorer**.
3. **Presupuesto y alertas (`AWS Budgets`):** **creado a mano** (no está en CloudFormation) y verificado el 18/11: `presupuesto-indice-del-taco`, **10 USD al mes** (≈ $200 MXN, bajo el tope de $250 MXN del SOW), con avisos sobre el gasto real al **50 %** y **80 %**. La cuenta tiene además un Budget de 1 USD (`My Zero-Spend Budget`). El límite de gasto de la cuenta se revisa en AWS Settings → Billing.
4. **Ciclo de vida en S3 (`LifecycleConfiguration`):** Purga automática de versiones no actuales a los 30 días (bronze, silver, gold, cuarentena y artefactos) y caducidad a los 7 días de los resultados de Athena. *(No se configuró la limpieza de cargas multiparte incompletas; es una mejora posible.)*

---

## 3. Verificación de gasto real (AWS Cost Explorer)

* **Crédito disponible en cuenta:** $140.00 USD (vigencia hasta 2027-05-16; verificado 18/11/2026 desde la consola de Billing).
* **Gasto del mes actual:** **$0.00 USD** al 18/11/2026 (consola de AWS, widget "Costo y uso", mes 11/2026).
* **Gasto acumulado por servicio del proyecto:** **sin medir todavía.** Pendiente del paso 3.1 (activar la etiqueta `project`).

### 3.1 Cómo activar la etiqueta `project` en Cost Explorer (B5)

Los recursos creados por CloudFormation ya llevan las etiquetas `project=indice-del-taco` y `environment=dev` (ver sección 2, punto 2). Para que Cost Explorer pueda filtrar el gasto por esas etiquetas hay que **activarlas como "Cost allocation tags"** una sola vez:

1. En la consola AWS, buscar y entrar a **Billing and Cost Management**.
2. En el menú lateral: **Cost allocation tags** (bajo "Billing & Payments preferences" → "Cost organization").
3. En la pestaña **User-defined tags**, buscar `project` y `environment` (puede haber que marcar "Show tags with values that match").
4. Marcar ambas y dar clic en **Activate**.
5. Esperar ~24 h (AWS tarda hasta un día en empezar a desglosar el gasto por la nueva etiqueta).

> Permisos requeridos: `ce:UpdateCostAllocationTagsStatus`. Lo tiene el admin de la cuenta; si no puede el responsable de plataforma, pedirle al dueño de la cuenta que lo haga.

### 3.2 Cómo anotar el gasto real (una vez activada la etiqueta)

Correr, al menos semanalmente durante lo que queda del proyecto, el siguiente comando (o entrar a Cost Explorer → Reports y filtrar por tag `project=indice-del-taco`):

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-11-01,End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter '{"Tags":{"Key":"project","Values":["indice-del-taco"]}}'
```

Y anotar el resultado en el cuadro de abajo. Si la etiqueta aún no desglosa (porque no han pasado las ~24 h), usar el filtro por la cuenta entera y aclararlo.

| Fecha de medición | Rango medido | Gasto real (USD) | Método | Notas |
| :--- | :--- | ---: | :--- | :--- |
| _por llenar_ | 01/11/2026 – ___ | _por llenar_ | tag `project=indice-del-taco` | primera medición después de activar la etiqueta |

### 3.3 Región, Budget y suscripciones (B6)

| Elemento | Valor verificado el 18/11/2026 | Fuente |
| :--- | :--- | :--- |
| Región del proyecto | `us-east-2` (US East — Ohio); ADR 0010 explica por qué | AWS Settings → Billing |
| Budget "presupuesto-indice-del-taco" | **10 USD/mes**, avisos al 50 % y 80 % del gasto real | AWS Budgets |
| Budget "My Zero-Spend Budget" | 1 USD, viene por defecto en cuentas nuevas | AWS Budgets |
| Tope de escaneo de Athena | 100 MB por consulta (`BytesScannedCutoffPerQuery`) | `infra/06-glue-athena.yaml` |
| Suscripciones SNS (`indice-del-taco-dev-alertas`) | Fernanda confirmada; una suscripción adicional por confirmar | Consola SNS → Subscriptions |

> **Pendiente de B6:** mover el Budget a una plantilla de CloudFormation para que se recree desde cero con `scripts/desplegar.sh`.