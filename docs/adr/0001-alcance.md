# ADR 0001: Alcance del proyecto

**Estado:** Aceptada
**Fecha:** 2026-10-22

## Contexto

La propuesta inicial incluía un tablero privado con autenticación, una plantilla de captura de precios en lugar de leer el chat del proveedor y Terraform como herramienta de infraestructura. Tras revisar la propuesta, el brief del proyecto y la sesión de descubrimiento con Doña Ofelia, algunas de estas decisiones desviaban el esfuerzo del núcleo del proyecto (ingeniería de datos) o contradecían el RFP. Además, la dueña mencionó otras necesidades (rentabilidad de las gringas, apps de reparto, franquicia) que no forman parte de este proyecto.

## Decisiones

### 1. Sin autenticación de usuarios en el dashboard

- **Opciones vistas:** dashboard con login (por ejemplo, con Cognito, API Gateway o CloudFront), página estática en S3, o dashboard público en Streamlit Community Cloud sobre un *snapshot* de las tablas gold.
- **Decisión:** dashboard público sin login que solo lee un *snapshot* de tablas gold agregadas (el detalle del hospedaje va en el ADR 0006).
- **Razón:** el RFP (§6) dice que el tablero público solo muestra índices y comparaciones; los precios del proveedor, las ventas y los mensajes se quedan en S3 privado y nunca llegan al dashboard. El candado debe estar en el almacenamiento (bloqueo de acceso público e IAM), no en la pantalla. El login es desarrollo web y agrega servicios complejos y costosos.
- **Consecuencia:** se eliminan del alcance el login, la prueba de usabilidad dedicada y la experiencia móvil como producto. Se mantiene el criterio de que las 4 preguntas se pueden leer en el dashboard. El snapshot público excluye las columnas con precios de compra exactos (por ejemplo `precio_don_beto`).

### 2. Procesar el chat exportado en lugar de usar una plantilla

- **Opciones vistas:** plantilla estructurada que llenaría el proveedor, conexión en vivo a WhatsApp, o procesar un archivo `.txt` exportado.
- **Decisión:** procesar el archivo `.txt` exportado; no se conecta a WhatsApp en vivo.
- **Razón:** la conexión en vivo es frágil y plantea riesgos de privacidad; la plantilla obliga al proveedor a cambiar su forma de trabajar. Limpiar datos sucios (precios con y sin `$`, cambios relativos, correcciones, mensajes sin precios) es parte del trabajo.
- **Consecuencia:** se agrega un parser con pruebas unitarias y un generador de datos sintéticos con semilla fija, porque en esta simulación el chat real no existe.

### 3. CloudFormation como herramienta de infraestructura como código

- **Opciones vistas:** Terraform, AWS CloudFormation y alternativas como SAM o CDK.
- **Decisión:** AWS CloudFormation, según la retroalimentación recibida. El brief del proyecto recomienda Terraform y acepta SAM o CDK si se documenta en un ADR; SAM y CDK generan CloudFormation. El detalle va en el ADR 0004.
- **Razón:** es nativa de AWS, sin dependencias externas.
- **Consecuencia:** cada hito aporta su parte de la plantilla para evitar dejar toda la infraestructura al final.

### 4. Servicios básicos dentro del free tier

- **Decisión:** usar EventBridge Scheduler, Lambda, S3, CloudWatch, SNS, IAM, Budgets y Glue Data Catalog; Athena con volúmenes pequeños. Evitar NAT Gateway, EC2 o RDS encendidos, Redshift, QuickSight, jobs de Glue ETL, SageMaker, Cognito, API Gateway y Step Functions salvo que sean indispensables.
- **Razón:** el costo mensual máximo es $300 MXN y un servicio mal elegido puede consumir los créditos en días.
- **Consecuencia:** se documenta el gasto real en `docs/costos.md`.

### 5. Qué se deja fuera aunque la dueña lo mencionó

- **Decisión:** quedan fuera la comparación con otras ciudades, la rentabilidad de las gringas, las comisiones y conciliaciones de las apps de reparto (Rappi, DiDi, Uber), la conciliación contable contra CONTPAQi y los números para el local de Coyoacán o la franquicia en Satélite.
- **Razón:** el RFP limita el proyecto a suadero y pastor en CDMX y excluye puntos de venta y facturación. Son necesidades reales del cliente, pero cada una es un proyecto aparte.
- **Consecuencia:** se registran como posibles ampliaciones y, si el cliente las pide, entran por el control de cambios del SOW.