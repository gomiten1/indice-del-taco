# Roadmap: del estado actual a un pipeline operacional

**Actualizado:** 2026-11-16 (noche) · **Entrega final:** 2026-11-27 (11 días) · **Reemplaza** el calendario del SOW §6, que ya no era realista.

El alcance y los criterios de aceptación siguen siendo los del [SOW](docs/consultoria/sow.md). Este documento ordena **qué está hecho, qué falta verificar, pulir y afinar**, y qué se sacrifica si falta tiempo.

Leyenda: ✅ hecho y verificado · 🔶 parcial o hecho sin verificar del todo · ⬜ pendiente · **D** debe · **S** debería · **X** después.

## Estado al 16/11 (noche)

El primer bloque funciona de punta a punta en AWS (`us-east-2`): **bronze → silver → gold → Athena**, orquestado cada lunes a las 6:00 (CDMX) y con registro de ejecuciones. Responde **P1** (costo por taco) y **P4** (contra la inflación) con datos sintéticos y el INPC real de Banxico. Todo está en commits locales (111 pruebas en verde); falta hacer push y abrir PR de la rama `feat/contratos-y-banxico`.

### Hecho (verificado)

| Área | Qué hay |
| :---- | :---- |
| Código | Generador sintético con semilla fija; parser del chat (C1 a C11); silver del chat, el INPC y la receta (cuarentena, particiones por año ISO y semana, idempotente); gold (`costo_taco_semanal` con índice base 100, merma solo en pastor, `precio_insumo_semanal`, `comparativo_inflacion`); handlers de Lambda (Banxico, silver, gold, orquestador) |
| AWS (7 stacks) | `bronze`, `lake` (silver, gold, cuarentena), `artefactos`, `banxico`, `pipeline` (silver y gold), `athena` (Glue con partition projection y workgroup con tope de 100 MB), `orquestacion` (Scheduler, SNS, alarmas) |
| Verificado en la cuenta | Banxico trae 694 registros, no reescribe si no cambió el contenido (ETag) y es idempotente; silver y gold se ejecutan; **gold en AWS es idéntico al cálculo local**; Athena devuelve P1 y P4 (< 1 KB escaneado); el orquestador hizo una corrida real y la registró (5 etapas en `ok`); la cuenta permite crear roles IAM |
| Documentación | RFP/SOW/aclaraciones, diccionario de datos v0, ADRs 0001, 0003, 0005, 0007, 0008, 0009 y 0010, `sql/` con P1 y P4 interpretadas, `infra/README.md` con los comandos de despliegue |

### Por verificar (se hizo, pero falta comprobarlo)

| Qué | Por qué falta | Cómo se cierra |
| :---- | :---- | :---- |
| **Alerta por correo (N5)** | La suscripción de SNS sigue **pendiente de confirmar**; no se lanzó la falla simulada | Confirmar el correo, lanzar `{"simular_falla":"silver"}` y comprobar que llega en ≤ 60 min |
| Alarmas de CloudWatch | Nunca se han disparado (errores del orquestador y "7 días sin ejecutarse") | Provocar un error real del orquestador y ver la alarma |
| Schedule semanal | La primera corrida automática es el lunes 23/11 | Ver al menos **dos** corridas sin intervención (E5) |
| Límite de gasto y región | No se confirmó en AWS Settings; el presupuesto no está creado | Confirmar región (`us-east-2`), límite de gasto y crear un Budget al 50 % y 80 % |
| Recrear todo desde cero | Las plantillas se desplegaron una por una, a mano | Destruir y volver a desplegar con un script (N6, E6) |
| Recalcular una semana desde bronze | Silver y gold son idempotentes, pero falta la prueba explícita | Prueba de reproducibilidad (3.6) |
| Gasto real | No hay cifra | `docs/costos.md` con Cost Explorer |

### Por pulir (trabajo pendiente)

| Qué | Nota |
| :---- | :---- |
| **P2 y P3** | Necesitan PROFECO: bajar los CSV a mano (descarga bloqueada con 403), filtrar CDMX, proxies de cortes y mayoreo con muestra mínima |
| Inflación de alimentos (N4) | Falta encontrar la serie; hoy solo hay INPC general |
| Dashboard y snapshot | Snapshot de gold sin precios exactos del proveedor + Streamlit |
| Runbook, costos y ADRs | Falta `runbook.md`, `costos.md` y los ADRs 0002 (capas/Parquet/catálogo), 0004 (CloudFormation), 0006 (Streamlit), PROFECO híbrida, SNIIM y proxies |
| Script de despliegue | Reemplazar los comandos sueltos por uno reproducible y unificar plantillas (00 a 07) |
| CI en GitHub | `pytest` y `cfn-lint` en cada PR; el CD con OIDC es opcional y se decide después (ver Pendientes de decidir) |
| Diagrama y README | Reflejar lo construido (hoy muestra una VPC y eventos de S3 que no existen) |
| Limpieza | Quitar o marcar como obsoleta `infra/02-lambda.yaml` (demo, no desplegada); decidir si `bronze_local/` (3.9 MB) se queda en git; `CLAUDE.md` sin seguimiento |
| Comparación CSV vs Parquet | Criterio de E3 pendiente |
| Equipo | Push y PR de las ramas, revisión por otra persona, reparto de responsables, enviar a la dueña las aclaraciones A1 a A6 |

### Por afinar (valores y decisiones provisionales)

Funcionan, pero son supuestos míos o del equipo, fáciles de cambiar:

| Parámetro o decisión | Valor actual | Dónde |
| :---- | :---- | :---- |
| Variación semanal sospechosa | > 25 % | `UMBRAL_VARIACION` (`silver_chat.py`) |
| Alerta de cuarentena | > 10 % de los registros | `UMBRAL_CUARENTENA` (`comun.py`) |
| Fuente atrasada (chat y Banxico) | > 10 días | `UMBRAL_REZAGO_DIAS` (`handlers/comun.py`) |
| Merma del pastor | 12 % | `MERMA_PASTOR` ([ADR 0008](docs/adr/0008-merma.md)) |
| Estadístico del precio, semana base, salsa | Mediana, primera semana completa, fuera del costo | ADR 0003, 0009 y 0005 |
| Tope de Athena, retención de logs, hora del schedule | 100 MB, 14 días, lunes 6:00 CDMX | `infra/06` y `07` |
| Datos sintéticos | Formato del chat, remitentes, texto de los mensajes, `vigente_desde` de la receta | [ADR 0007](docs/adr/0007-datos-sinteticos-reconstruccion.md) |
| Costo del taco | Solo la carne (sin tortilla ni verduras) | [ADR 0005](docs/adr/0005-salsa.md) |

Todas las decisiones están como "aceptada provisionalmente" y esperan la revisión del equipo y las respuestas de la dueña (A1 a A6).

## Principio de recorte

Un pipeline pequeño que corre de punta a punta vale más que cinco capas a medias.

## Fases

### Fase 0 · Cimientos y decisiones

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 0.1 | ✅ | Verificar y desplegar la base en AWS (ver [ADR 0010](docs/adr/0010-cuenta-aws-y-region.md)) | D |
| 0.2 | 🔶 | Seguridad de la cuenta: en la nueva experiencia de AWS el acceso humano lo administra AWS (no hay MFA de root ni usuarios IAM propios). Falta confirmar el límite de gasto y crear el Budget | D |
| 0.3 | ✅ | Contratos de datos: `docs/diccionario_datos.md` v0 (falta revisión del equipo) | D |
| 0.4 | 🔶 | ADRs críticos: hechos 0003, 0005, 0008, 0009 y 0010; faltan 0002, 0004, 0006, PROFECO híbrida, SNIIM, proxies de pastor y suadero | D |
| 0.5 | ⬜ | Reparto real de tareas por persona; cada cambio entra por PR revisado por otra persona (SOW §7) | D |
| 0.6 | 🔶 | Receta fijada (55 g de suadero, 50 g de pastor); faltan tortilla, verduras y la tabla de equivalencias, y enviar las aclaraciones A1 a A6 | D |
| 0.7 | ✅ | Brief ausente: se reconstruyó y se documentó en el ADR 0007 | D |

### Fase 1 · Datos de entrada

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 1.1 | ✅ | Generador sintético con semilla fija (chat, receta, ventas) con errores intencionales | D |
| 1.2 | ✅ | Parser del chat de WhatsApp con pruebas (26) | D |
| 1.3 | ✅ | Lambda de Banxico: idempotente, sin reescribir si no cambió, token en Parameter Store | D |
| 1.4 | ⬜ | PROFECO: carga manual de al menos una quincena de CDMX a bronze (`bMM_AAAA_qN`) | D |
| 1.5 | ✅ | Buckets silver, gold, cuarentena y artefactos | D |
| 1.6 | ⬜ | Lambda de INEGI (falta el ID del INPC) | X |
| 1.7 | ⬜ | Serie de inflación de alimentos en Banxico o INEGI | D |

### Fase 2 · Silver y calidad

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 2.1 | 🔶 | Silver desplegado para chat, INPC y receta; falta PROFECO | D |
| 2.2 | ⬜ | Resolver duplicados de PROFECO (~11 k combinaciones repetidas por quincena) | D |
| 2.2b | ⬜ | Leer los CSV de PROFECO (223 MB) por partes sin exceder memoria ni tiempo de Lambda | D |
| 2.3 | 🔶 | Reglas de calidad hechas para chat, INPC y receta; falta aplicarlas a PROFECO | D |
| 2.4 | ✅ | Glue Data Catalog (DDL manual, partition projection) y Athena | D |
| 2.5 | ⬜ | Comparación de bytes escaneados CSV vs Parquet (E3) | D |

### Fase 3 · Gold e Índice del Taco

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 3.0 | ✅ | Salsa y merma decididas (ADR 0005 y 0008) | D |
| 3.1 | ✅ | `costo_taco_semanal` e índice base 100 | D |
| 3.2 | 🔶 | `precio_insumo_semanal` (proveedor) hecho; falta `comparativo_proveedor` (P2) | D |
| 3.3 | 🔶 | `comparativo_inflacion` con INPC general; falta alimentos | D |
| 3.4 | ⬜ | `contribucion_insumo` (P3, necesita más insumos) | D |
| 3.5 | 🔶 | SQL de P1 y P4 en `sql/`; faltan P2 y P3 | D |
| 3.6 | 🔶 | Reproducibilidad: silver y gold son idempotentes; falta la prueba de recalcular una semana desde bronze | D |
| 3.7 | ✅ | Sensibilidad con merma (versión aparte para el pastor) | S |

### Fase 4 · Operación

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 4.1 | 🔶 | EventBridge Scheduler (lunes 6:00 CDMX) desplegado; falta ver dos corridas automáticas | D |
| 4.2 | ✅ | Alarmas, SNS y registro de ejecuciones desplegados; alertas por fallas y por datos sospechosos o atrasados | D |
| 4.3 | ⬜ | **Falla simulada** y correo recibido en ≤ 60 min (bloqueado: suscripción pendiente de confirmar) | D |
| 4.4 | 🔶 | Plantillas 00 a 07 desplegadas; falta unificarlas, el script y la prueba destruir → desplegar | D |
| 4.5 | ⬜ | Runbook por alerta (`docs/runbook.md`) | D |
| 4.6 | 🔶 | Un rol de mínimo privilegio por Lambda ya definido; falta la prueba de permisos | D |
| 4.7 | ⬜ | CI en GitHub (`pytest` y `cfn-lint` por PR) | S |

### Fase 5 · Producto y entrega

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 5.1 | ⬜ | Snapshot de gold sin precios exactos, versionado en `snapshot_gold/` | D |
| 5.2 | ⬜ | Dashboard en Streamlit (P1 a P4) que declara los supuestos y marca lo aproximado | D |
| 5.3 | ⬜ | `docs/costos.md` con el gasto real | D |
| 5.4 | 🔶 | Al menos 5 ADRs (hay 7), diccionario final, README final con hallazgos y aprendizajes | D |
| 5.5 | ⬜ | Presentación de 10 minutos y video demo de 3 a 5 minutos | D |
| 5.6 | ⬜ | Guía de réplica para otro negocio (N8); si se recorta, queda como limitación aprobada | S |
| 5.7 | ⬜ | Actualizar el diagrama y los checkboxes de Avance del README | D |
| 5.8 | ⬜ | Prueba de N7 con la dueña (4 preguntas en < 5 minutos) y acta de entrega | D |

## Línea de corte

Si el 24/11 no están cerradas las fases 1 a 3, se recorta en este orden:

1. Se quita: guía de réplica y la comparación CSV vs Parquet (como limitación documentada).
2. Se acepta: PROFECO solo con una o dos quincenas cargadas a mano. El histórico sintético (ene a sep 2026) y las quincenas deben **alinearse en fechas**; donde no coincidan se muestra "sin dato".
3. Se acepta: dashboard mínimo (índice, costo por taco, comparación con inflación) y el resto en tablas.
4. **No se recorta:** idempotencia, cuarentena, alerta con falla simulada, IaC y que el dashboard no exponga datos sensibles.

## Definición de "operacional"

- [ ] El pipeline corre bronze → silver → gold sin intervención, al menos dos veces seguidas, y el costo por taco queda listo antes del lunes 9:00. *(corrió una vez a mano; la primera automática es el 23/11)*
- [x] Volver a correr una semana no duplica registros ni cambia resultados. *(verificado en Banxico, silver y gold; falta la prueba explícita desde bronze)*
- [x] Un dato malo va a cuarentena y se reporta, no se usa.
- [ ] Una falla simulada manda correo en ≤ 60 min y queda registrada.
- [ ] Todo se recrea desde las plantillas, sin credenciales en el repo. *(no hay credenciales en el repo; falta la prueba de recreación)*
- [ ] El dashboard público solo muestra índices y comparaciones.
- [ ] Alarma de Budgets activa y gasto real documentado.
- [ ] La dueña responde las 4 preguntas en el dashboard en menos de 5 minutos, o la limitación queda documentada.

## Riesgos que pueden mover este plan

| Riesgo | Qué hacer |
| :---- | :---- |
| PROFECO sigue dando 403 | Carga manual de una o dos quincenas; el ADR lo documenta como ingesta híbrida |
| Mayoreo (N2) con muestra mínima en la Central de Abasto (tortilla 2, cilantro 1) | Marcar la comparación como aproximada y mostrar "sin dato" |
| CSV de PROFECO de 223 MB exceden memoria o tiempo de Lambda | Leer por partes y filtrar al leer (2.2b) |
| Inflación de alimentos no disponible en las fuentes probadas | Tarea 1.7; si no existe, documentarlo como limitación |
| La alerta de correo nunca se ha probado | Cerrar 4.3 primero: es el único criterio crítico sin evidencia |
| Todo vive en la cuenta personal de una persona | Plantillas y script de despliegue para recrearlo en otra cuenta (ADR 0010) |
| Dependencias de cliente (A1 a A6) sin responder | Se trabaja con los supuestos provisionales y el dashboard los declara |
| El plan gratuito de AWS tiene crédito y vigencia limitados (120 USD hasta 16/05/2027) | Revisar Budgets y Cost Explorer en cada fase |

## Pendientes de decidir

Se deciden en equipo y se registran en un ADR.

- **¿CD desde GitHub?** CI (tests y lint) sí es seguro y barato. El despliegue automático con OIDC depende de que la cuenta permita crear el proveedor de identidad, y de quién puede hacer merge a `main` (desplegaría en la cuenta personal).
- **Orquestación:** quedó implementada con EventBridge Scheduler y una Lambda orquestadora, no con eventos de S3 como dice el README. Falta registrarlo en un ADR y corregir el README.
- **VPC en el diagrama:** el SOW evita NAT y servidores encendidos; el diagrama dibuja una VPC.
- **SNIIM descartado e INEGI como limitación:** el SOW los incluye. Cambian el alcance y, según el SOW §11, los aprueba la dueña por escrito.
- **Usuarios del equipo:** el SOW dice "un usuario IAM por integrante"; la cuenta usa *team members* ([ADR 0010](docs/adr/0010-cuenta-aws-y-region.md)).

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
