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

* **Crédito disponible en cuenta:** $120.00 USD (vigencia hasta 2027-05-16).
* **Gasto acumulado:** **sin medir todavía.** Falta anotar el valor de AWS Cost Explorer (filtrando por la etiqueta `project=indice-del-taco`, que hay que activar como etiqueta de costos en Billing).