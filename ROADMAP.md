# Roadmap: del estado actual a un pipeline operacional

**Creado:** 2026-11-16 · **Entrega final:** 2026-11-27 (11 días) · **Reemplaza** el calendario del SOW §6, que ya no es realista (H2 a H4 vencidos).

El alcance y los criterios de aceptación siguen siendo los del [SOW](docs/consultoria/sow.md). Este documento solo reordena y recorta **qué se hace primero y qué se sacrifica si falta tiempo**.

## Dónde estamos (16/11)

| Hecho | Falta |
| :---- | :---- |
| RFP, SOW, aclaraciones, ADR 0001, diagrama | Todo el código: `src/`, `sql/`, `datos_sinteticos/`, `tests/`, `dashboard/` |
| `docs/fuentes.md` validado (Banxico OK, PROFECO bloqueado, INEGI sin ID) | Generador sintético y parser del chat |
| Plantillas CloudFormation base (bucket bronze y Lambda demo) | Silver, gold, índice, calidad, cuarentena |
| Ingesta local manual en `bronze_local/` | Orquestación, alertas, Budgets, IaC completa |
| | ADRs 0002 a 0006, diccionario, runbook, costos |

**No verificado:** si algo de `infra/` se desplegó en AWS. Se confirma en la Fase 0.

## Principio de recorte

Un pipeline pequeño que corre de punta a punta vale más que cinco capas a medias. Todo se prioriza así:

- **Debe (D):** sin esto no hay proyecto operacional.
- **Debería (S):** se hace si D va en tiempo.
- **Después (X):** se documenta como mejora futura, no se construye.

## Fases

### Fase 0 · Cimientos y decisiones (16 a 17/11)

Sin esto el equipo no puede trabajar en paralelo.

| # | Tarea | Prio | Resultado |
| :---- | :---- | :---- | :---- |
| 0.1 | Verificar qué hay desplegado en AWS (stacks `indice-taco-bronze` y `indice-taco-extract`) | D | Estado anotado en `infra/README.md` |
| 0.2 | MFA en root, un usuario IAM por integrante, Budgets al 50% y 80% | D | Captura de la alarma activa |
| 0.3 | ✅ (v0, falta revisión del equipo) Congelar los **contratos de datos**: esquema de silver y de las 5 tablas gold (columnas y tipos). La receta y los precios de proveedor son **datos o configuración**, no valores fijos en el código (requisito de N8) | D | `docs/diccionario_datos.md` v0 |
| 0.4 | Decidir y escribir ADRs críticos: ingesta híbrida de PROFECO, descarte de SNIIM, frecuencia por fuente, proxies de pastor y suadero, capas, Parquet y catálogo (ADR 0002). Estadístico (0003), salsa (0005), merma (0008) y semana base (0009) ya decididos provisionalmente | D | ADRs 0002, 0003 y los listados en `fuentes.md` |
| 0.5 | Reparto real de tareas por persona (los roles del SOW son nominales). Cada cambio entra por PR revisado por otra persona (SOW §7) | D | Tabla de responsables al final de este archivo |
| 0.6 | Fijar receta (55 g de suadero, 50 g de pastor), catálogo de insumos y tabla de equivalencias de cortes con sus supuestos por escrito; enviar a la dueña las aclaraciones A1 a A6 | D | Receta e insumos en `datos_sinteticos/` y `aclaraciones.md` actualizado |
| 0.7 | Conseguir el **brief del proyecto** (el SOW lo cita para el extracto del chat y el Anexo A de casos del parser; no está en el repo) | D | Brief disponible antes de la tarea 1.2 |

**Por qué los contratos primero:** quien hace gold no espera a silver si ya sabe qué columnas va a recibir; quien hace silver no espera al generador si ya sabe el formato de entrada.

### Fase 1 · Datos de entrada (17 a 19/11)

| # | Tarea | Prio | Resultado |
| :---- | :---- | :---- | :---- |
| 1.1 | ✅ Generador sintético con semilla fija: chat del proveedor, receta, ventas (ene a sep 2026) con errores intencionales | D | `datos_sinteticos/`, misma semilla da mismos datos |
| 1.2 | ✅ Parser del chat de WhatsApp (con y sin `$`, unidades implícitas, cambios relativos, correcciones, "lo demás igual") | D | `src/`, pruebas unitarias en verde |
| 1.3 | ✅ Código y pruebas listos; **falta desplegar y probar en AWS**. Lambda de ingesta de Banxico a bronze: idempotente, con `fecha_ingesta`, token en Parameter Store | D | Doble ejecución sin duplicados, logs en CloudWatch |
| 1.4 | PROFECO: script de carga manual a bronze (una quincena de CDMX como mínimo) | D | CSV en bronze, nombre `bMM_AAAA_qN` como llave |
| 1.5 | ✅ Plantilla lista (`infra/03`); **falta desplegar**. Buckets silver, gold y cuarentena (plantillas hermanas de `01-s3-bucket.yaml`) | D | Stacks desplegados |
| 1.6 | Lambda de ingesta de INEGI (falta el ID del INPC) | X | Banxico cubre el INPC general; se anota como limitación (cambio de alcance, ver "Pendientes de decidir") |
| 1.7 | Encontrar y probar en Banxico (o INEGI) la serie de **inflación de alimentos**; N4 pide inflación general y de alimentos | D | Serie probada y anotada en `fuentes.md`; si no existe, limitación documentada |

### Fase 2 · Silver y calidad (19 a 21/11)

| # | Tarea | Prio | Resultado |
| :---- | :---- | :---- | :---- |
| 2.1 | Lambda de limpieza: tipos, catálogo de insumos, normalización de unidades a kg/pieza, filtro CDMX | D | Parquet particionado por año/semana |
| 2.2 | Resolver duplicados de PROFECO (hay ~11k combinaciones repetidas por quincena) | D | Regla documentada y probada |
| 2.2b | Leer los CSV de PROFECO (223 MB) por partes, filtrando CDMX y columnas, sin exceder memoria ni tiempo de Lambda | D | Decisión en ADR; prueba con un archivo real |
| 2.3 | Reglas de calidad: precio > 0, fecha válida, unidad reconocida, variación semanal razonable, esquema esperado, completitud; umbral de cuarentena que dispara alerta | D | Cuarentena trazable, pruebas unitarias |
| 2.4 | Glue Data Catalog (DDL manual) y consultas en Athena | D | Tablas consultables en `sql/` |
| 2.5 | Comparación de bytes escaneados CSV vs. Parquet (criterio de E3) | D | Número en el README |

### Fase 3 · Gold e Índice del Taco (20 a 23/11)

Arranca en paralelo con la Fase 2 usando datos sintéticos y los contratos de la Fase 0.

| # | Tarea | Prio | Resultado |
| :---- | :---- | :---- | :---- |
| 3.0 | ✅ Costeo de la salsa y merma decididos (ADR 0005 y 0008) | D | ADR 0005 |
| 3.1 | `costo_taco_semanal` e Índice base 100: `Σ cantidad_por_taco × precio_unitario` | D | Tabla gold, pruebas del cálculo |
| 3.2 | `precio_insumo_semanal` y `comparativo_proveedor` (proveedor vs. menudeo y mayoreo PROFECO). Si falta el dato público de un insumo, se muestra "sin dato" | D | Tablas gold, marcadas como comparación aproximada |
| 3.3 | `comparativo_inflacion` (índice vs. inflación general y de alimentos, misma base 100; frecuencia mensual) | D | Tabla gold |
| 3.4 | `contribucion_insumo` (top 3 insumos del último trimestre) | D | Tabla gold |
| 3.5 | Una consulta SQL por pregunta (P1 a P4), con su interpretación | D | `sql/p1.sql` a `p4.sql` |
| 3.6 | Recalcular una semana desde bronze y comprobar que da el mismo resultado | D | Prueba de reproducibilidad (N6) |
| 3.7 | Sensibilidad con merma (ADR 0005) | S | Segunda versión del índice |

### Fase 4 · Operación (23 a 25/11)

| # | Tarea | Prio | Resultado |
| :---- | :---- | :---- | :---- |
| 4.1 | EventBridge Scheduler semanal que dispara el pipeline completo en orden, con corte el domingo 23:59 y resultado listo antes del lunes 9:00 (N1) | D | Al menos **dos** corridas completas sin intervención (durante las pruebas se dispara más seguido que cada semana) |
| 4.2 | Alarmas de CloudWatch y SNS por correo ante fallas **y datos sospechosos** (variación semanal extrema, cuarentena sobre el umbral); registro de ejecuciones (fecha, fuente, leídos, aceptados, rechazados, duración) | D | Tabla o log de ejecuciones |
| 4.3 | **Falla simulada a propósito** y correo recibido en ≤60 min | D | Captura del correo (N5) |
| 4.4 | Unificar las plantillas CloudFormation; probar destruir y volver a desplegar | D | Grabación (N6, E6) |
| 4.5 | Runbook por alerta | D | `docs/runbook.md` |
| 4.6 | Roles IAM de mínimo privilegio y prueba de permisos | D | Revisión de los roles de cada Lambda |

### Fase 5 · Producto y entrega (24 a 27/11)

| # | Tarea | Prio | Resultado |
| :---- | :---- | :---- | :---- |
| 5.1 | Snapshot de gold **sin** precios de compra exactos, versionado en `snapshot_gold/` | D | Archivos de snapshot |
| 5.2 | Dashboard en Streamlit que responda P1 a P4, claro para una persona no técnica; declara los supuestos provisionales y marca las comparaciones aproximadas | D | URL pública |
| 5.3 | `docs/costos.md` con el gasto real | D | Número real de AWS |
| 5.4 | Al menos 5 ADRs en total (incluidos 0004 CloudFormation y 0006 Streamlit sobre snapshot), diccionario de datos final, `aclaraciones.md` actualizado, README final con hallazgos y aprendizajes | D | Documentación completa |
| 5.5 | Presentación de 10 minutos sin tecnicismos y video demo de 3 a 5 minutos | D | Archivos de entrega |
| 5.6 | Guía de réplica para otro negocio: cambiar receta y precios sin modificar código (N8). Si se recorta, se documenta como limitación aprobada | S | Sección en el README |
| 5.7 | Actualizar el diagrama de arquitectura y el README para que reflejen lo construido (marcar los checkboxes de Avance) | D | Diagrama y README al día |
| 5.8 | Prueba de N7 con la dueña (responde las 4 preguntas en menos de 5 minutos), retroalimentación y acta de entrega | D | Acta de entrega; limitaciones anotadas |

## Línea de corte

Si el 24/11 no están cerradas las fases 1 a 3, se recorta en este orden:

1. Se quita: guía de réplica y sensibilidad con merma (ambos como limitación documentada).
2. Se acepta: PROFECO solo con una o dos quincenas cargadas a mano. El histórico sintético (ene a sep 2026) y las quincenas de PROFECO deben **alinearse en fechas**; donde no coincidan se muestra "sin dato".
3. Se acepta: dashboard mínimo (índice, costo por taco, comparación con inflación) y el resto en tablas.
4. **No se recorta:** idempotencia, cuarentena, alerta con falla simulada, IaC y que el dashboard no exponga datos sensibles.

## Definición de "operacional"

- [ ] El pipeline corre bronze → silver → gold sin intervención, al menos dos veces seguidas, y el costo por taco queda listo antes del lunes 9:00.
- [ ] Volver a correr una semana no duplica registros ni cambia resultados.
- [ ] Un dato malo va a cuarentena y se reporta, no se usa.
- [ ] Una falla simulada manda correo en ≤60 min y queda registrada.
- [ ] Todo se recrea desde las plantillas, sin credenciales en el repo.
- [ ] El dashboard público solo muestra índices y comparaciones.
- [ ] Alarma de Budgets activa y gasto real documentado.
- [ ] La dueña responde las 4 preguntas en el dashboard en menos de 5 minutos, o la limitación queda documentada.

## Riesgos que pueden mover este plan

| Riesgo | Qué hacer |
| :---- | :---- |
| El generador sintético se retrasa y bloquea todo lo demás | Es la tarea 1.1, la primera en arrancar; mientras tanto se trabaja con los contratos de la Fase 0 |
| PROFECO sigue dando 403 | Carga manual de una o dos quincenas; el ADR lo documenta como ingesta híbrida |
| No se resuelve el ID del INPC de INEGI | Se usa solo Banxico y se anota como limitación |
| Dependencias de cliente (aclaraciones A1 a A6) sin responder | Se trabaja con los supuestos provisionales y el dashboard los declara |
| Servicios de AWS fuera del free tier | Revisar Budgets en cada fase |
| Mayoreo (N2) con muestra mínima: la Central de Abasto de CDMX en PROFECO trae pocas filas (tortilla 2, cilantro 1) | Marcar la comparación como aproximada y mostrar "sin dato" cuando falte |
| CSV de PROFECO de 223 MB exceden la memoria o el tiempo de Lambda | Leer por partes y filtrar al leer (tarea 2.2b) |
| Inflación de alimentos no disponible en las fuentes probadas | Tarea 1.7; si no existe, documentarlo como limitación |

## Pendientes de decidir

Contradicciones del repo que el roadmap no resuelve. Se decide en equipo y se registra en un ADR.

- **¿Quién dispara silver y gold?** El README dice eventos de S3; el SOW dice EventBridge. La tarea 4.1 asume EventBridge, pero queda por confirmar.
- **VPC en el diagrama:** el SOW evita NAT y servidores encendidos; el diagrama dibuja una VPC.
- **SNIIM descartado e INEGI como limitación:** el SOW los incluye. Cambian el alcance y, según el SOW §11, los aprueba la dueña por escrito.

## Responsables

*Por asignar en la tarea 0.5.*

| Fase | Responsable | Apoyo |
| :---- | :---- | :---- |
| 0 | | |
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
