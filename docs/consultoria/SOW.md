EQUIPO 2 · PROPUESTA DE SERVICIOS

# **SOW | El Índice del Taco**

Declaración de trabajo 

| Consultora |  |
| :---- | :---- |
| **Cliente** | La TaquerIA Opus · Representante: Doña Ofelia Ruvalcaba |
| **Respuesta al RFP del** | 06/10/2026 · Propuesta elaborada: 12/10/2026 |
| **Versión** | 1.0 · Propuesta sujeta a aprobación del cliente |
| **Periodo propuesto** | 21/10/2026 a 27/11/2026 |
| **Equipo** | Gerardo Arredondo Granados (líder); Fernanda García Ortega (datos); Carlos López Estrada (infraestructura); Alejandro Martínez Jiménez (calidad); Emilio Sebastián Ospino Mérida (dashboard). |

# **1\. Resumen ejecutivo**

La TaquerIA Opus necesita conocer el costo semanal de sus tacos de suadero y pastor y saber si los incrementos de sus insumos se justifican frente al mercado. Proponemos un sistema con captura controlada de precios y recetas, comparaciones con fuentes públicas y un tablero privado fácil de consultar. El sistema actualizará la información semanalmente, detectará datos anómalos y avisará por correo cuando falle una actualización. Incluye infraestructura recreable y documentación para operar o adaptar la solución a otro negocio. **Entrega propuesta: 27/11/2026; precio total estimado: \$828,959.20 MXN, IVA incluido**, con operación estimada en **\$250 MXN mensuales** (sujeta a consumo real).

# **2\. Alcance**

**Dentro de alcance**

•  Definir y documentar las recetas estándar por taco; capturar precios del proveedor mediante una plantilla estructurada, sin leer conversaciones automáticamente.

•  Integrar y homologar información semanal aplicable de SNIIM (mayoreo), PROFECO (menudeo) e INEGI (inflación general y alimentos); Banxico solo como fuente auxiliar si aporta contexto.

•  Calcular costo por taco en pesos e índice base 100, comparación porcentual de insumos y contribución al cambio de costo trimestral; conservar insumos originales y versiones del cálculo.

•  Publicar un dashboard **privado con autenticación**, consultable desde móvil, con explicaciones sencillas y visualizaciones que respondan las cuatro preguntas del cliente.

•  Automatizar el proceso semanal, prevenir duplicaciones, aislar datos incorrectos, registrar ejecución y enviar alertas por correo en menos de una hora ante fallas o datos sospechosos.

•  Desplegar en AWS sin servidores permanentes mediante infraestructura como código; aplicar permisos mínimos, protección de datos, monitoreo de gasto y entregar documentación y pruebas.

**Fuera de alcance**

•  Punto de venta, inventario y facturación: no forman parte del problema de comparación de costos.

•  Predicción de precios o fijación automática de precios de venta: se ofrecerá análisis histórico, no pronósticos.

•  Compras o negociación automática con proveedores: las decisiones comerciales quedan en manos de la dueña.

•  Actualización en tiempo real: la frecuencia semanal satisface el objetivo y mantiene bajos los costos.

•  Otros productos, otros tipos de taco o ciudades distintas de CDMX: requieren ampliación del alcance.

•  Aplicación móvil nativa o lectura automática de WhatsApp: el acceso será web y la carga de precios será controlada.

•  Difusión pública de precios exactos, ventas o datos del proveedor: son información confidencial.

# **3\. Entregables y criterios de aceptación**

| \# | Entregable | Criterio de aceptación | Hito |
| :---- | :---- | :---- | :---- |
| E1 | Datos normalizados y catálogo de insumos | Plantillas, recetas aprobadas y equivalencias de unidades; fuentes/fechas visibles; registros inválidos separados y trazables. | H2 |
| E2 | Cálculo semanal e Índice del Taco | Costo MXN por taco (suadero/pastor), índice base 100 y recálculo idéntico para una misma semana; prueba de ejecución repetida sin duplicados. | H3 |
| E3 | Comparaciones de mercado e inflación | Diferencia % frente a SNIIM y PROFECO por insumo comparable; gráfico del índice y las dos series INEGI con misma base y fechas señaladas. | H4 |
| E4 | Análisis de variación de costos | Ranking trimestral de aportaciones y presentación de los 3 insumos principales con su %; cálculo contrastado con casos de prueba. | H4 |
| E5 | Dashboard privado y prueba de usabilidad | Acceso por cuenta autorizada, lectura desde celular y prueba con Doña Ofelia: 4 preguntas contestadas sin ayuda en menos de 5 min. | H4 / H6 |
| E6 | Actualización semanal, control y alertas | Programación semanal; resultado antes del lunes 09:00 en pruebas piloto y seguimiento de meta ≥95% de semanas; correo ≤60 min tras falla/anomalía simulada; bitácora. | H5 |
| E7 | Infraestructura segura y recreable | Terraform desplegable, privilegios mínimos, secretos protegidos, monitoreo y alertas presupuestales activas desde el primer día. | H5 |
| E8 | Entrega documental y guía de réplica | GitHub con README, diccionario, ADRs, runbook y reporte de costos; otro negocio piloto cambia recetas/precios mediante guía sin modificar código. | H6 |

Nota de medición: la meta de disponibilidad semanal del 95% se verificará con pruebas de ejecución y un mecanismo de seguimiento en producción; no puede acreditarse con semanas reales antes de finalizar el proyecto.

# **4\. Trazabilidad con el RFP**

| Necesidad del RFP | Entregable(s) | Estado propuesto |
| :---- | :---- | :---- |
| N1 · Costo semanal por taco | E1, E2, E6 | Cubierta |
| N2 · Precio del proveedor vs. mercado | E1, E3, E5 | Cubierta |
| N3 · Insumos que explican aumentos | E2, E4, E5 | Cubierta\* |
| N4 · Costo frente a inflación | E2, E3, E5 | Cubierta |
| N5 · Alertas sin fallas silenciosas | E6, E7 | Cubierta |
| N6 · Calidad y reproducibilidad | E1, E2, E6, E7 | Cubierta |
| N7 · Facilidad de comprensión | E5 | Cubierta |
| N8 · Adaptación a otro negocio | E1, E7, E8 | Cubierta |

\* N3 depende de contar con suficiente historial trimestral; si falta, se evidenciará el cálculo con pruebas señaladas como demostración y se mostrará solo el periodo de datos reales disponible.

# **5\. Enfoque técnico (alto nivel)**

| Recetas y precios capturados de forma autorizada  \+  SNIIM / PROFECO / INEGI |
| :---: |
| **↓  Captura programada · conversión de unidades · validación y cuarentena** |
| **↓  Histórico protegido · cálculo de costo, índice y comparaciones** |
| **↓  Dashboard privado y reportes     ↔     Bitácoras, alertas y control de gasto** |

Se propone una arquitectura **batch serverless en AWS**: programación semanal (EventBridge), procesamiento por demanda (Lambda), almacenamiento protegido e histórico (S3) y seguimiento de eventos y errores (CloudWatch con notificaciones por correo). Una interfaz web autenticada mostrará los resultados sin exponer los datos del proveedor. Los datos se normalizarán a unidades comparables; cada fuente conservará su fecha y procedencia. Los registros incompletos, inconsistentes o atípicos irán a cuarentena y no alterarán el indicador publicado. Cada semana tendrá una versión de cálculo reproducible y con capacidad de reprocesamiento sin duplicados . Terraform permitirá recrear recursos; IAM restringirá los accesos y las alarmas de costos se configurarán al inicio. Las decisiones definitivas, los servicios seleccionados y sus justificaciones quedarán en ADR-001 (almacenamiento), ADR-002 (fuentes/equivalencias) y ADR-003 (seguridad/despliegue) dentro del repositorio que se entregará.

# **6\. Plan por hitos**

| Hito | Qué se entrega | Evidencia | Fecha | Horas |
| :---- | :---- | :---- | :---- | ----: |
| H0 · Arranque | Alcance validado, acceso y plan de trabajo | Acta de inicio, backlog, responsables | 21/10/2026 | 40 |
| H1 · Definición | Recetas, reglas, prototipos y criterios N1–N8 | Minuta firmada; prototipo revisado | 27/10/2026 | 170 |
| H2 · Datos | Fuentes, plantilla de captura, homologación y E1 | Dataset trazable y pruebas de validación | 03/11/2026 | 235 |
| H3 · Motor de cálculo | E2, historial, índice y reproceso idempotente | Pruebas de cálculo y doble ejecución | 10/11/2026 | 240 |
| H4 · Tablero y análisis | E3, E4 y E5 en ambiente de pruebas | Demostración con fuentes y acceso privado | 17/11/2026 | 155 |
| H5 · Operación | E6, E7; monitoreo, alertas y Terraform | Prueba de fallo, restauración y costos | 24/11/2026 | 115 |
| H6 · Cierre | E8; ajustes, capacitación y aceptación | Acta final y réplica guiada | 27/11/2026 | 35 |
| TOTAL | 7 hitos | 5 integrantes · 21/10 al 27/11 |  | 990 |

Las fechas suponen aprobación del proyecto el 20/10/2026 y disponibilidad oportuna de las fuentes y del cliente. Retrasos ajenos al equipo se gestionan mediante control de cambios (§11).

# **7\. Equipo y responsabilidades**

| Integrante | Rol | Responsabilidad principal | Reporta a |
| :---- | :---- | :---- | :---- |
| Arredondo Granados Gerardo | Líder de proyecto | Alcance, arquitectura funcional, cronograma, decisiones, relación con cliente, integración y aceptación. | Doña Ofelia |
| García Ortega Fernanda | Ingeniería de datos | Ingesta, catálogo de insumos, fuentes públicas, normalización, cálculo y trazabilidad. | Líder |
| López Estrada Carlos | Infraestructura y seguridad | AWS, Terraform, IAM, despliegue, monitoreo, alertas y presupuesto cloud. | Líder |
| Martínez Jiménez Alejandro | Calidad de datos | Reglas de validación, cuarentena, pruebas de integridad, reproducibilidad y criterios de calidad. | Líder |
| Ospino Mérida Emilio Sebastián | Análisis y dashboard | Indicadores, comparativas, experiencia móvil, visualizaciones y pruebas de usabilidad. | Líder |

# **8\. Supuestos y dependencias del cliente**

•  Doña Ofelia designará un enlace y aprobará las recetas, cantidades por taco, insumos y reglas de cálculo a más tardar en H1; las recetas en papel y la variación entre preparadores deberán conciliarse.

•  El cliente compartirá precios históricos o recientes del proveedor en un formato autorizado, con fecha, producto, cantidad y unidad; el equipo no extraerá mensajes de WhatsApp sin intervención.

•  Las referencias de SNIIM, PROFECO e INEGI tendrán disponibilidad y condiciones de consulta compatibles; las equivalencias de cortes/productos (p. ej., suadero o pastor) se documentarán y requerirán visto bueno.

•  Cuando falten semanas, datos públicos o equivalencias válidas, se indicará “sin dato” o “último dato disponible”, sin inventar precios ni ocultar ausencias.

•  Los datos de ventas no son indispensables para el costo unitario solicitado; no se construirá un módulo comercial de ventas. Datos sintéticos podrán emplearse solo para pruebas claramente identificadas.

•  La dueña facilitará retroalimentación del tablero (H4), una prueba de lectura no asistida (H6), una cuenta de correo receptora de alertas y autorización de acceso a AWS o ambiente acordado.

•  Se asumirá operación ligera y una cuenta/ambiente AWS proporcionado por el cliente; variaciones importantes de consumo, acceso a fuentes o carga de usuarios implican reevaluar el costo mensual.

# **9\. Riesgos**

| Riesgo | Prob. | Impacto | Qué haremos |
| :---- | :---- | :---- | :---- |
| Cambios, caídas o retrasos de SNIIM / PROFECO / INEGI | Alta | Alto | Versionar adaptadores, detectar desfases, registrar último dato válido y alertar; no publicar datos fingidos. |
| Referencia pública no equivalente al insumo real | Alta | Alto | Tabla de equivalencias y aprobación de Doña Ofelia; marcar comparaciones aproximadas. |
| Precios con unidades mixtas o captura incorrecta | Alta | Alto | Plantilla normalizada, conversiones verificables y cuarentena con notificación. |
| Sin histórico de un trimestre para N3 | Media | Medio | Mostrar periodo real; probar fórmula con datos de prueba identificados y completar trimestre con el tiempo. |
| Falla silenciosa o ejecución duplicada | Media | Alto | Controles de idempotencia, bitácoras, pruebas de reintento y alarmas ≤60 min. |
| Acceso indebido a datos de proveedor | Media | Alto | Autenticación, roles mínimos, cifrado, secretos protegidos y prueba de permisos. |
| Costos AWS \> \$300/mes | Media | Medio | Presupuesto/alertas desde H0, servicios por demanda, prueba de costos y ajuste del consumo. |
| Demoras en validación por parte del cliente | Media | Medio | Revisiones dos veces por semana; registro de pendientes y escalamiento en 2 días hábiles. |

# **10\. Presupuesto**

| Concepto | Horas | Tarifa MXN/h | Subtotal MXN |
| :---- | ----: | ----: | ----: |
| Liderazgo / coordinación | 190 | \$700.00 | \$133,000.00 |
| Ingeniería de datos | 210 | \$650.00 | \$136,500.00 |
| Infraestructura y seguridad | 190 | \$700.00 | \$133,000.00 |
| Calidad de datos | 190 | \$580.00 | \$110,200.00 |
| Análisis y dashboard | 210 | \$650.00 | \$136,500.00 |
| **Subtotal de servicios** | **990** | **—** | **\$649,200.00** |
| Colchón de imprevistos (10%) | — | — | \$64,920.00 |
| AWS estimado durante el proyecto (2 meses × \$250) | — | — | \$500.00 |
| **Subtotal antes de impuestos** | **—** | **—** | **\$714,620.00** |
| **IVA estimado (16%)** | **—** | **—** | **\$114,339.20** |
| **TOTAL PROPUESTO, IVA incluido** | **990** | **—** | **\$828,959.20** |

Comparación con el RFP: límite total \$900,000.00 MXN; margen disponible \$71,040.80 MXN (7.9%). Supuesto: el tope incluye IVA y una reserva por imprevistos; la reserva solo se utiliza con autorización. Montos propuestos, no cotizaciones verificadas de terceros.

Operación AWS posterior: objetivo \$250 MXN/mes, por debajo del máximo de \$300 MXN/mes. Es una estimación de bajo volumen, no una tarifa garantizada. Se configurarán alertas de consumo desde H0 y se documentará el gasto observado antes de la aceptación.

# **11\. Control de cambios y comunicación**

Habrá seguimiento interno continuo y **revisión con Doña Ofelia dos veces por semana** (martes y viernes), por correo o reunión breve, con minuta de acuerdos y pendientes. El líder será el punto único de contacto; incidencias de ejecución se registrarán en el repositorio y las fallas críticas se comunicarán por correo según E6.

Toda solicitud fuera del alcance se registrará con descripción, justificación e impacto en plazo, costo, riesgos y criterios de aceptación. El líder presentará la evaluación y **solo Doña Ofelia aprobará por escrito** el cambio antes de implementarlo. Se actualizarán SOW, backlog y cronograma cuando aplique; los cambios no autorizados no forman parte de la entrega contratada.

# **12\. Aceptación y pagos**

Un hito se considerará terminado cuando el equipo entregue su evidencia, se ejecute la demostración o prueba acordada y Doña Ofelia confirme su aceptación por escrito. El cliente tendrá **2 días hábiles** para revisar y reportar observaciones concretas; el equipo resolverá defectos críticos antes de solicitar la aceptación nuevamente. La falta de respuesta no equivale a aprobación automática. H6 cerrará con acta de entrega, acceso al repositorio, manuales, capacitación y confirmación de seguridad y funcionalidad.

**Distribución propuesta de pagos** (porcentajes sobre el precio total IVA incluido):

| Hito de aceptación | Porcentaje | Monto MXN |
| :---- | ----: | ----: |
| H0 · Inicio aprobado | 5% | \$41,447.96 |
| H1 · Definición aprobada | 10% | \$82,895.92 |
| H2 · Datos validados | 20% | \$165,791.84 |
| H3 · Cálculos aceptados | 25% | \$207,239.80 |
| H4 · Dashboard validado | 20% | \$165,791.84 |
| H5 · Automatización y seguridad | 15% | \$124,343.88 |
| H6 · Entrega final aceptada | 5% | \$41,447.96 |
| TOTAL | 100% | \$828,959.20 |

**Condiciones de cierre:** todas las necesidades N1–N8 deberán contar con evidencia de cumplimiento o limitaciones documentadas y aprobadas; las pruebas de usabilidad, recuperación, idempotencia, protección de datos y alertamiento deberán quedar registradas. Las dependencias no disponibles se anotarán en el acta de aceptación y no se presentarán como resultados reales ya verificados.