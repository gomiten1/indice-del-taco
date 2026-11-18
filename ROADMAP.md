# Roadmap: del estado actual a un pipeline operacional

**Actualizado:** 2026-11-18 · **Entrega final:** 2026-11-27 · **Reemplaza** el calendario del SOW §6, que ya no era realista.

El alcance y los criterios de aceptación siguen siendo los del [SOW](docs/consultoria/sow.md). Este documento ordena **qué está hecho, qué falta verificar, pulir y afinar**, y qué se sacrifica si falta tiempo.

Leyenda: ✅ hecho y verificado · 🔶 parcial o hecho sin verificar del todo · ⬜ pendiente · **D** debe · **S** debería · **X** después.

## Para terminar: lista para quien continúe

Todo lo de abajo está **sin hacer**, ordenado de más a menos urgente. Lo construido y verificado está en [Estado](#estado-al-1811); el detalle técnico, en `docs/runbook.md` y `infra/README.md`. Fecha límite: **27/11**.

### A. Esta semana (desbloquea lo demás)

| # | Qué hacer | Cómo se sabe que está listo |
| :---- | :---- | :---- |
| A1 | **Hacer push de `feat/profeco-silver-p2` y abrir el PR** (silver de PROFECO, P2 y los ADR 0020 a 0022); revisión de otra persona | PR fusionado y CI en verde (confirma la tarea 4.7) |
| A2 | **SNS:** aceptar el correo de confirmación o reenviarlo; decidir quién recibe las alertas | `list-subscriptions` sin «PendingConfirmation». La pendiente expira ≈ 19/11 04:32 UTC |
| A3 | **Ver correr solo el schedule** el lunes 23/11 6:00 CDMX (y una segunda corrida el 30/11 si hay tiempo) | Dos filas `ok` en `registro_ejecuciones` sin intervención (E5) |
| A4 | **Enviar a la dueña** las aclaraciones A1 a A6 y las preguntas 1 a 8 de [`aclaraciones.md`](docs/consultoria/aclaraciones.md) | Respuestas anotadas con fecha. Las dos que bloquean cosas: **7** (umbral ±10 % de P2) y **8** (gramos por taco y peso del manojo) |
| A5 | **Asignar responsables** (sección «Responsables» de abajo) | Tabla llena |

### B. Operación y reproducibilidad

| # | Qué hacer | Cómo se sabe que está listo |
| :---- | :---- | :---- |
| B1 | **Script de despliegue** (`scripts/desplegar.sh`) que reemplace los comandos sueltos de `infra/README.md`; unificar las plantillas 00 a 07 si conviene | Un solo comando crea todo desde cero |
| B2 | **Prueba destruir → desplegar** (N6, E6). Cuidado: borrar el stack de orquestación borra el tema SNS y sus suscripciones; los buckets son `Retain` | Todo recreado y una corrida `ok`; anotar el tiempo |
| B3 | **Prueba de recálculo desde bronze** (3.6): borrar silver y gold, relanzar, comparar con el snapshot | Resultado idéntico |
| B4 | **Alarma real:** provocar un error del orquestador para ver una alarma pasar a ALARM y un correo con su hora; guardar la captura (cierra 4.3) | Captura en `docs/` |
| B5 | **Gasto real:** activar la etiqueta `project` en Billing y anotar el valor de Cost Explorer en `docs/costos.md` §3 | Cifra con fecha |
| B6 | **Confirmar región y límite de gasto** en AWS Settings. La región es `us-east-2` y **probablemente no se puede cambiar** (la fija la dirección de contacto, ADR 0010); si se pudiera, hay que rehacer todo (haz B1 y B2 antes) | Nota en el ADR 0010 |
| B7 | Mínimo privilegio: probar que cada Lambda **no** puede hacer lo que no debe (4.6) | Prueba anotada |

### C. Producto y entrega

| # | Qué hacer | Cómo se sabe que está listo |
| :---- | :---- | :---- |
| C1 | **Decidir público o privado** el dashboard: el RFP §7 dice «privado y de acceso seguro»; el SOW §6 y el ADR 0001 dicen público. Propuesta: público mientras los datos sean sintéticos, con ADR y visto bueno de la dueña | ADR escrito |
| C2 | **Publicar el dashboard** en Streamlit Community Cloud (`dashboard/app.py`, lee `snapshot_gold/`); agregar un aviso visible de que **los datos del proveedor son sintéticos** | URL pública abierta sin login |
| C3 | **Corregir la imagen del diagrama** (quitar la VPC y los eventos de S3; poner orquestador, PROFECO manual y la región real; INEGI fuera) o usar el Mermaid del README | Imagen actualizada |
| C4 | **README final** con hallazgos (taco +12.3 % contra INPC +1.7 %, P2) y aprendizajes | Revisado por el equipo |
| C5 | **Presentación de 10 minutos y video demo de 3 a 5 minutos** | Archivos en el repo o enlace |
| C6 | **Prueba de N7 con la dueña:** 4 preguntas en menos de 5 minutos y acta de entrega | Acta firmada |

### D. Datos (cuando se consigan)

| # | Qué hacer | Cómo |
| :---- | :---- | :---- |
| D1 | **Más quincenas de PROFECO** (junio y primera de julio) para ampliar P2 | Runbook §9; cada CSV se sube a `raw/profeco/fecha_ingesta=.../` y se relanza el orquestador |
| D2 | **Gramos por taco de tortilla, cebolla, cilantro, limón y piña** (y peso de un manojo) | Respuesta de la dueña (A4/pregunta 8); agregar filas a `receta.csv`; P3 se completa solo |
| D3 | **Datos reales** del chat del proveedor y ventas | Sustituyen a los sintéticos; revisar el riesgo de privacidad del ADR 0012 antes de publicar |
| D4 | **Aprobaciones escritas de la dueña** de los ADR 0011, 0015, 0018 y 0022 (SOW §11) | Anotarlas en cada ADR |

### E. Opcionales (solo si sobra tiempo)

- Despliegue automático desde GitHub: OIDC está bloqueado en esta cuenta; opciones en «Pendientes de decidir» (CodeBuild con CodeConnections, CodePipeline, o CI más script).
- INEGI como contraste del INPC (tarea 1.6).
- Corregir el respaldo de merma del dashboard (`× 1.12` debería ser `÷ 0.88`; solo se usa si faltan las filas con merma).
- Decidir si `bronze_local/` (≈ 4.6 MB con la muestra de PROFECO) se queda en git; `CLAUDE.md` está sin versionar a propósito.

### Qué no se recorta

Idempotencia, cuarentena, alerta con falla simulada, IaC y que el dashboard no exponga datos sensibles. Si falta tiempo, se recorta en el orden de «Línea de corte».

## Estado al 18/11

El pipeline funciona de punta a punta en AWS (`us-east-2`): **bronze → silver → gold → Athena**, orquestado cada lunes a las 6:00 (CDMX), con registro de ejecuciones, alertas por correo y un **dashboard de Streamlit** que lee un snapshot de gold. Responde **P1**, **P2** y **P4** con datos sintéticos del proveedor, el INPC real de Banxico y precios reales de PROFECO (**solo del 16 al 31 de julio de 2026**, ADR 0020); **P3** solo trae la carne con valor porque la receta no tiene más insumos.

### Hecho

| Área | Qué hay |
| :---- | :---- |
| Código | Generador sintético; parser del chat (C1 a C11); silver del chat, el INPC y la receta (cuarentena, particiones, idempotente); gold con cuatro tablas (costo e índice base 100, precio por insumo, inflación y **P3 con "sin dato"**); handlers de Lambda (Banxico, silver, gold, orquestador); `pipeline_local` (todo el pipeline sin AWS); `snapshot` (exporta gold a los CSV del dashboard, reproducible y sin columnas del proveedor). **126 pruebas** |
| AWS (7 stacks) | `bronze`, `lake`, `artefactos`, `banxico`, `pipeline`, `athena` y `orquestacion` (Scheduler, SNS, alarmas) |
| Verificado en la cuenta (16/11 y 18/11) | Banxico idempotente y sin reescribir si no cambió; gold en AWS idéntico al cálculo local; Athena devuelve P1, P4 y **P3** (33 filas idénticas al snapshot); el orquestador corrió completo el 18/11 (estado `ok`, sin alertas) con el código nuevo en las tres Lambdas |
| Dashboard y snapshot | `dashboard/app.py` (P1 a P4, avisa "Aún sin datos" y "Sin dato"), `dashboard/requirements.txt`, `snapshot_gold/` generado desde gold (reproduce byte a byte el del PR #9) |
| Documentación | **22 ADRs** (0001 a 0022), diccionario v0, `runbook.md` y `costos.md` corregidos, guía de réplica completa, `sql/` con P1 y P4 interpretadas, `infra/README.md` |
| Alertas y Budget (verificado en AWS el 18/11) | La **falla simulada se probó el 17/11** (ver abajo); el Budget `presupuesto-indice-del-taco` existe (10 USD al mes, avisos reales al 50 % y 80 %) |

### Por verificar (se hizo, pero falta comprobarlo)

| Qué | Por qué falta | Cómo se cierra |
| :---- | :---- | :---- |
| **Alerta por correo (N5)** | **Verificado en AWS:** el 17/11 18:17 UTC se registró `FallaSimulada` en silver y Banxico sí corrió y gold no; la alarma `orquestador-errores` pasó a ALARM a las 18:19 y volvió a OK a las 18:33. **No verificado:** que el correo llegó y en cuánto tiempo | Guardar la captura del correo (la recibió Fernanda) y anotar la hora |
| **Suscripciones de SNS** | Hay dos: una **confirmada (Fernanda)** y una **pendiente (la tuya)**; las pendientes se borran a las 48 h (≈ 19/11 04:32 UTC) | Aceptar el correo o reenviar la confirmación; decidir quién debe recibir las alertas |
| Alarmas de CloudWatch | Nunca se han visto disparar solas | Provocar un error real del orquestador |
| Schedule semanal | La primera corrida automática es el lunes 23/11 | Ver al menos **dos** corridas sin intervención (E5) |
| Límite de gasto y región | El Budget **sí existe** (se creó a mano, no está en CloudFormation); falta revisar el límite de gasto y confirmar la región en AWS Settings | Confirmar `us-east-2` y el límite en AWS Settings; si se quiere reproducible, agregar el Budget a una plantilla |
| Recrear todo desde cero | Las plantillas se desplegaron una por una | Script de despliegue y prueba destruir → desplegar (N6, E6) |
| Recalcular una semana desde bronze | Silver y gold son idempotentes, falta la prueba explícita | Prueba de reproducibilidad (3.6) |
| Gasto real | `costos.md` solo tiene estimaciones | Medir en Cost Explorer (activar la etiqueta `project`) |
| Dashboard público | Solo se probó con Streamlit simulado | Publicarlo en Streamlit Community Cloud y revisar la URL |

### Por pulir (trabajo pendiente)

| Qué | Nota |
| :---- | :---- |
| ~~P2 y P3 completos~~ | **P2 hecho el 18/11** con el CSV de julio (semanas 29 a 31); P3 con más insumos depende de los gramos por taco de la dueña ([ADR 0022](docs/adr/0022-p2-mercado-unidades-y-diagnostico.md)) |
| ~~Inflación de alimentos (N4)~~ | **Hecha el 18/11** (`SP66540` y `SP56386`, automática por la API) |
| Script de despliegue | Reemplazar los comandos sueltos por uno reproducible y unificar plantillas (00 a 07) |
| CI en GitHub | `pytest` y `cfn-lint` en cada PR (el CD con OIDC se decide después) |
| Imagen del diagrama | La de Diagramon sigue mostrando una VPC y eventos de S3; el diagrama vigente es el del README |
| Limpieza | Decidir si `bronze_local/` (3.9 MB) se queda en git; `CLAUDE.md` sin seguimiento |
| Equipo | PRs de las ramas, revisión por otra persona, reparto de responsables, enviar a la dueña las aclaraciones A1 a A6 |
| Presentación y video | Presentación de 10 minutos y video demo de 3 a 5 minutos |

### Por afinar (valores y decisiones provisionales)

| Parámetro o decisión | Valor actual | Dónde |
| :---- | :---- | :---- |
| Variación semanal sospechosa | > 25 % | `UMBRAL_VARIACION`; [ADR 0016](docs/adr/0016-reglas-y-umbrales-de-calidad.md) |
| Alerta de cuarentena | > 10 % de los registros | `UMBRAL_CUARENTENA` |
| Fuente atrasada (chat y Banxico) | > 10 días | `UMBRAL_REZAGO_DIAS`; [ADR 0014](docs/adr/0014-frecuencia-y-rezago-por-fuente.md) |
| Merma del pastor | 12 % | `MERMA_PASTOR`; [ADR 0008](docs/adr/0008-merma.md). *El respaldo del dashboard usa `× 1.12`; lo correcto sería `÷ 0.88`. Solo se usa si faltan las filas con merma* |
| Estadístico, semana base, salsa | Mediana, primera semana completa, fuera del costo | ADR 0003, 0009 y 0005 |
| **Privacidad del snapshot** | Riesgo aceptado: el costo en pesos permite estimar el precio del proveedor | [ADR 0012](docs/adr/0012-privacidad-del-snapshot.md); revisar antes de publicar con datos reales |
| **Umbral de «caro» o «barato» en P2** | **Abierto, lo puse yo:** ±10 % contra el menudeo | `UMBRAL_DIAGNOSTICO_PCT` en `gold.py`; [ADR 0022](docs/adr/0022-p2-mercado-unidades-y-diagnostico.md). Pregunta 7 de `aclaraciones.md`: lo debe definir la dueña |
| Cobertura de PROFECO | Solo 16 al 31 de julio de 2026 (un CSV) | [ADR 0020](docs/adr/0020-profeco-csv-y-cobertura.md); se amplía cargando más quincenas |
| Insumos esperados por taco (P3) | pastor, tortilla, cebolla, cilantro, limón, piña (y suadero sin piña) | `INSUMOS_ESPERADOS` en `gold.py` |
| Tope de Athena, retención de logs, hora del schedule | 100 MB, 14 días, lunes 6:00 CDMX | `infra/06` y `07` |
| Datos sintéticos | Formato del chat, remitentes, mensajes, `vigente_desde` de la receta | [ADR 0007](docs/adr/0007-datos-sinteticos-reconstruccion.md) |
| Costo del taco | Solo la carne | [ADR 0005](docs/adr/0005-salsa.md) |

Todas las decisiones están como "aceptadas provisionalmente" y esperan la revisión del equipo. Tres requieren además la **aprobación escrita de la dueña** (SOW §11): los proxies de pastor y suadero (ADR 0015), dejar INEGI y SNIIM fuera del alcance (ADR 0011 y 0018) y el umbral de ±10 % de P2 (ADR 0022).

## Datos que faltan y cómo conseguirlos

Lo que más limita hoy al proyecto no es código sino **datos**. Esta es la lista, en orden de utilidad, con lo que desbloquea cada uno.

| # | Dato | Desbloquea | Estado hoy | Quién y cuánto cuesta |
| :---- | :---- | :---- | :---- | :---- |
| 1 | ~~Precios de PROFECO~~ | P2 | **Cargado el 18/11:** `b07_2026_q2.csv`, CDMX, **16 al 31 de julio de 2026** ([ADR 0020](docs/adr/0020-profeco-csv-y-cobertura.md)). Más quincenas ampliarían las semanas con comparación | Cualquiera, con el runbook §9 |
| 2 | ~~Serie de inflación de alimentos~~ **Hecha** | N4 completa | **Implementada y desplegada el 18/11**, automática por la API de Banxico | Nadie: ya está |
| 3 | Datos reales del cliente (receta completa, chat real, ventas) y respuestas a las aclaraciones | Costo completo, N7, N8 | Solo hay datos sintéticos y supuestos | Líder, con Doña Ofelia o Diego |
| 4 | ID del INPC en INEGI | Contraste del INPC (opcional, [ADR 0018](docs/adr/0018-inflacion-con-banxico.md)) | Bloqueado | Opcional, baja prioridad |
| 5 | El *brief* original del proyecto | Casos reales del parser | Reconstruido ([ADR 0007](docs/adr/0007-datos-sinteticos-reconstruccion.md)) | Opcional |

### 1. PROFECO: precios de mercado (cargado el 18/11)

**Estado:** el CSV `b07_2026_q2.csv` ya está en bronze y alimenta P2. **Cobertura: 16 al 31 de julio de 2026** (semanas ISO 29 a 31), registrada en `registro_ejecuciones`. El cilantro va por manojo. Para ampliar, cargar más quincenas (runbook §9). Lo que sigue describe cómo conseguirlas.

**Qué es:** el programa *Quién es quién en los precios*, publicado en datos.gob.mx como un CSV por quincena. Es la única fuente de mercado
del proyecto (menudeo y, con las filas de Central de Abasto, mayoreo). SNIIM se descartó ([ADR 0011](docs/adr/0011-ingesta-hibrida-profeco-sniim.md)).

**Por qué es a mano:** el 14/11 los 55 CSV devolvieron `403` (protección Akamai) a `curl`, desde una máquina local. **No se ha probado desde AWS.**
Desde un navegador sí se descargan.

**Dónde:** <https://www.datos.gob.mx/dataset/programa_quien_es_quien_precios_2026> (cada recurso tiene su botón de descarga).

**Qué hay en 2026** (lista leída de los metadatos de CKAN del 14/11; el dataset se actualizó por última vez el 22/09/2026):

| Mes | Archivos publicados |
| :---- | :---- |
| Enero | `b01_2026_q1.csv`, `b01_2026_q2.csv` |
| Febrero | `b02_2026_q2.csv` (**falta** la primera quincena) |
| Marzo y abril | **no hay** |
| Mayo | `b05_2026_q1.csv`, `b05_2026_q2.csv` |
| Junio | `b06_2026_q1.csv`, `b06_2026_q2.csv` |
| Julio | `b07_2026_q1.csv`, `b07_2026_q2.csv` |
| Agosto en adelante | **no hay** (todavía no publicados) |

Los datos sintéticos del chat cubren de enero a septiembre, así que donde PROFECO no tenga archivo la comparación saldrá como **«sin dato»**
([ADR 0019](docs/adr/0019-datos-faltantes-sin-dato.md)); no se interpola.

**Qué descargar, por prioridad:**
1. **Mínimo, para probar el pipeline:** `b07_2026_q2.csv`. Es el que ya validamos: 223.5 MB, 744,623 filas, 15 columnas, UTF-8 con BOM; CDMX son 157,076 filas.
2. **Recomendado:** julio completo (`b07_2026_q1` y `q2`) y junio (`b06_2026_q1` y `q2`). Julio es el único mes del tercer trimestre disponible, que es el que usa P3.
3. **Ideal:** los 9 archivos de 2026 (cada uno pesa del orden de 200 MB; solo se midió el de `b07_2026_q2`).

**Cómo:**
1. Abrir la página del dataset y descargar cada archivo con el navegador. Conservar el nombre original (`bMM_AAAA_qN.csv`: es la llave de idempotencia).
2. Guardarlos en `data/profeco/` (esa carpeta no se sube a git).
3. Comprobar cada uno: debe tener 15 columnas y la primera es `producto` (con BOM invisible); `wc -l` debe dar cientos de miles de líneas.
4. Subirlos a bronze (o pasármelos y los subo yo con una URL prefirmada):
   ```bash
   aws s3 cp data/profeco/b07_2026_q2.csv s3://indice-del-taco-dev-bronze-<ID-DE-CUENTA>/raw/profeco/csv/b07_2026_q2.csv
   ```

**Lo que hago yo cuando lleguen** (roadmap 1.4, 2.2, 2.2b, 3.2, 3.4):
silver de PROFECO (filtro CDMX y columnas leyendo por partes, para no pasar la memoria de Lambda; regla para los ~11 mil duplicados por quincena), la tabla de equivalencias
de cortes ([ADR 0015](docs/adr/0015-proxies-pastor-y-suadero.md), pendiente de la aprobación de la dueña), `comparativo_proveedor` (P2), más insumos en P3, la tabla de Athena y,
con un archivo real, la **repetición de la prueba Parquet contra CSV** ([`docs/parquet-vs-csv.md`](docs/parquet-vs-csv.md)).

**Límites a tener presentes:** PROFECO es quincenal y gold es semanal (se agrupa por `fecha_registro`); la muestra de mayoreo en Central de Abasto es pequeña
(tortilla 2 filas, cilantro 1 en esa quincena); no hay pastor ni suadero, solo proxies.

### 2. Inflación de alimentos (Banxico): resuelta y automática

**Hecho el 18/11.** El sitio del SIE usa endpoints de catálogo que no están en la documentación (incluida una **búsqueda por texto** sin token); con ellos salieron las claves,
comprobadas contra un CSV del SIE (538 meses, sin diferencias). Detalle en [`docs/fuentes.md`](docs/fuentes.md#catálogo-del-sie-y-claves-de-la-inflación-18112026).

| Serie | Clave | En el pipeline |
| :---- | :---- | :---- |
| INPC general | `SP1` | Obligatoria (base de P4) |
| **Alimentos, Bebidas y Tabaco** (subyacente: productos procesados) | **`SP66540`** | `inpc_alimentos_base100` |
| **Pecuarios** (no subyacente: el más cercano a la carne) | **`SP56386`** | `inpc_pecuarios_base100` |

La Lambda de Banxico trae las tres cada lunes, silver las combina (los meses `N/E`, sin dato, se omiten sin error) y gold las rebasa al mismo mes base que el índice del taco.
Resultado, enero a septiembre: taco **+12.3 %**, INPC general +1.7 %, alimentos +2.0 %, pecuarios **−2.6 %** ([`sql/README.md`](sql/README.md)).

**INEGI (opcional, sin urgencia):** solo serviría para contrastar el INPC de Banxico; la inflación de alimentos ya no depende de él ([ADR 0018](docs/adr/0018-inflacion-con-banxico.md)).

### 3. Datos reales del cliente y aclaraciones

Hoy el chat del proveedor, la receta y las ventas son **sintéticos**. Para que el índice sea del negocio y no una demostración hace falta pedirle a Doña Ofelia (o a Diego, su sobrino):

| Qué pedir | Para qué |
| :---- | :---- |
| **Exportación real del chat de WhatsApp** con Don Beto (`.txt`) | Precios reales; **probar el parser con el formato real** (se asumió el de Android, [ADR 0007](docs/adr/0007-datos-sinteticos-reconstruccion.md)) |
| **Receta completa**: gramos de tortilla, cebolla, cilantro, limón, piña y salsa por taco | Que el costo no sea solo la carne ([ADR 0005](docs/adr/0005-salsa.md)) |
| **Ventas** (exportes de caja) | Dato de apoyo, no entra al índice |
| Respuestas a **A1 a A6** y a las 6 preguntas pendientes de [`aclaraciones.md`](docs/consultoria/aclaraciones.md) | Confirmar el aumento («30 %» contra ≈ 12 %), tacos por kilo, merma, desde cuándo comparar |
| **Aprobación por escrito** de los proxies (ADR 0015) y de dejar INEGI y SNIIM fuera (ADR 0011 y 0018) | SOW §11: son cambios de alcance |

**Ojo con la privacidad:** el chat real trae nombre y teléfono del proveedor. Va **solo a bronze privado**; nunca al repositorio ni al dashboard.

### 4. El *brief* original (opcional)

El SOW lo cita para el extracto del chat y los casos del parser; no está en el repositorio. Si el equipo lo tiene, pasarlo para comparar con lo reconstruido.

## Principio de recorte

Un pipeline pequeño que corre de punta a punta vale más que cinco capas a medias.

## Fases

### Fase 0 · Cimientos y decisiones

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 0.1 | ✅ | Verificar y desplegar la base en AWS (ver [ADR 0010](docs/adr/0010-cuenta-aws-y-region.md)) | D |
| 0.2 | 🔶 | Seguridad de la cuenta: el acceso humano lo administra AWS (no hay MFA de root ni usuarios IAM propios). El Budget de 10 USD existe; falta revisar el límite de gasto en AWS Settings | D |
| 0.3 | ✅ | Contratos de datos: `docs/diccionario_datos.md` v0 (falta revisión del equipo) | D |
| 0.4 | ✅ | ADRs críticos: 22 escritos, entre ellos capas (0002), CloudFormation (0004), Streamlit (0006), PROFECO y SNIIM (0011), orquestación (0013) y proxies (0015); todos provisionales | D |
| 0.5 | ⬜ | Reparto real de tareas por persona; cada cambio entra por PR revisado por otra persona (SOW §7) | D |
| 0.6 | 🔶 | Receta fijada (55 g y 50 g); faltan tortilla, verduras y cilantro (gramos por taco) y la aprobación de equivalencias; enviar las aclaraciones A1 a A8 | D |
| 0.7 | ✅ | Brief ausente: se reconstruyó y se documentó en el ADR 0007 | D |

### Fase 1 · Datos de entrada

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 1.1 | ✅ | Generador sintético con semilla fija (chat, receta, ventas) con errores intencionales | D |
| 1.2 | ✅ | Parser del chat de WhatsApp con pruebas | D |
| 1.3 | ✅ | Lambda de Banxico: idempotente, sin reescribir si no cambió, token en Parameter Store | D |
| 1.4 | 🔶 | PROFECO: `b07_2026_q2.csv` cargado a bronze (`raw/profeco/fecha_ingesta=2026-11-18/`). Falta bajar más quincenas (junio y la primera de julio) para ampliar P2 | Cualquiera |
| 1.5 | ✅ | Buckets silver, gold, cuarentena y artefactos | D |
| 1.6 | ⬜ | Lambda de INEGI (se descarta por ahora, ADR 0018; solo contrastaría el INPC). Ver «Datos que faltan §2» | X |
| 1.7 | ✅ | Inflación de alimentos: `SP66540` (Alimentos, Bebidas y Tabaco) y `SP56386` (Pecuarios), automática por la API; desplegada y verificada en Athena el 18/11 | D |

### Fase 2 · Silver y calidad

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 2.1 | ✅ | Silver desplegado para chat, INPC, receta y PROFECO | D |
| 2.2 | ✅ | Duplicados de PROFECO: una fila por tienda, producto y día; si difieren, la mediana ([ADR 0021](docs/adr/0021-reglas-silver-profeco.md)) | D |
| 2.2b | ✅ | CSV de 220 MB leído por bloques de 8 MB: 57 s en AWS de punta a punta, con silver a 1 GB y 240 s | D |
| 2.3 | ✅ | Reglas de calidad para chat, INPC, receta y PROFECO ([ADR 0016](docs/adr/0016-reglas-y-umbrales-de-calidad.md), [0021](docs/adr/0021-reglas-silver-profeco.md)) | D |
| 2.4 | ✅ | Glue Data Catalog (DDL manual, partition projection) y Athena | D |
| 2.5 | ✅ | Comparación de bytes escaneados CSV vs Parquet medida el 18/11: 98 % a 100 % menos con Parquet ([`docs/parquet-vs-csv.md`](docs/parquet-vs-csv.md)). Repetir con una quincena real de PROFECO | D |

### Fase 3 · Gold e Índice del Taco

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 3.0 | ✅ | Salsa y merma decididas (ADR 0005 y 0008) | D |
| 3.1 | ✅ | `costo_taco_semanal` e índice base 100 | D |
| 3.2 | ✅ | `precio_insumo_semanal` (proveedor y mercado, por kg o manojo) y `comparativo_proveedor` (P2), desplegados; en Athena igual al snapshot (9 filas) | D |
| 3.3 | ✅ | `comparativo_inflacion` con INPC general, alimentos y pecuarios (misma base 100); en Athena coincide con el snapshot | D |
| 3.4 | ✅ | `contribucion_insumo` (P3) con "sin dato", **desplegada el 18/11**; en Athena coincide fila por fila con el snapshot (33 filas). Falta completarla con más insumos cuando haya PROFECO | D |
| 3.5 | ✅ | SQL de P1, P2, P3 y P4 en `sql/` | D |
| 3.6 | 🔶 | Reproducibilidad: silver y gold son idempotentes; falta la prueba explícita desde bronze | D |
| 3.7 | ✅ | Sensibilidad con merma (versión aparte para el pastor) | S |

### Fase 4 · Operación

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 4.1 | 🔶 | EventBridge Scheduler (lunes 6:00 CDMX) desplegado; falta ver dos corridas automáticas | D |
| 4.2 | ✅ | Alarmas, SNS y registro de ejecuciones desplegados; alertas por fallas y por datos sospechosos o atrasados | D |
| 4.3 | ✅ | **Falla simulada** probada el 17/11 (registro `error` en silver y alarma en ALARM → OK). Falta solo la captura del correo con su hora | D |
| 4.4 | 🔶 | Plantillas 00 a 07 desplegadas; falta unificarlas, el script y la prueba destruir → desplegar | D |
| 4.5 | ✅ | Runbook por alerta (`docs/runbook.md`, con los nombres reales) | D |
| 4.6 | 🔶 | Un rol de mínimo privilegio por Lambda ya definido; falta la prueba de permisos | D |
| 4.7 | 🔶 | CI en GitHub (`.github/workflows/ci.yml`: `pytest`, `cfn-lint` y snapshot al día) escrito; falta confirmar que corre en verde en un PR | S |

### Fase 5 · Producto y entrega

| # | Estado | Tarea | Prio |
| :---- | :---- | :---- | :---- |
| 5.1 | ✅ | Snapshot de gold sin precios del proveedor, generado con `transformacion.snapshot` | D |
| 5.2 | 🔶 | Dashboard en Streamlit (P1 a P4) listo y probado en local; falta la URL pública | D |
| 5.3 | 🔶 | `docs/costos.md` con estimaciones; el Budget ya existe; falta medir el gasto real | D |
| 5.4 | 🔶 | ADRs (hay 22) y diccionario hechos; falta el README final con hallazgos y aprendizajes | D |
| 5.5 | ⬜ | Presentación de 10 minutos y video demo de 3 a 5 minutos | D |
| 5.6 | 🔶 | Guía de réplica escrita; con limitaciones (productos e insumos van en el código) | S |
| 5.7 | 🔶 | Diagrama real de la arquitectura en el README (Mermaid). Si se necesita para la presentación, regenerar la imagen de Diagramon (la actual está desactualizada) | D |
| 5.8 | ⬜ | Prueba de N7 con la dueña (4 preguntas en < 5 minutos) y acta de entrega | D |

## Línea de corte

Si el 24/11 no están cerradas las fases 1 a 3, se recorta en este orden:

1. Se quita: nada de lo ya hecho; lo primero en recortarse sería la prueba con datos reales de PROFECO.
2. Se acepta: PROFECO solo con una o dos quincenas cargadas a mano. El histórico sintético y las quincenas deben **alinearse en fechas**; donde no coincidan se muestra "sin dato".
3. Se acepta: P2 y P3 como "Aún sin datos" en el dashboard.
4. **No se recorta:** idempotencia, cuarentena, alerta con falla simulada, IaC y que el dashboard no exponga datos sensibles.

## Definición de "operacional"

- [ ] El pipeline corre bronze → silver → gold sin intervención, al menos dos veces seguidas, y el costo por taco queda listo antes del lunes 9:00. *(corrió una vez a mano; la primera automática es el 23/11)*
- [x] Volver a correr una semana no duplica registros ni cambia resultados. *(falta la prueba explícita desde bronze)*
- [x] Un dato malo va a cuarentena y se reporta, no se usa.
- [x] Una falla simulada manda correo en ≤ 60 min y queda registrada. *(registrada en `registro_ejecuciones` y con la alarma disparada; falta la captura del correo con su hora)*
- [ ] Todo se recrea desde las plantillas, sin credenciales en el repo. *(no hay credenciales en el repo; falta la prueba de recreación)*
- [ ] El dashboard público solo muestra índices y comparaciones. *(listo en local; el riesgo del costo en pesos está aceptado en el ADR 0012; falta publicarlo)*
- [ ] Alarma de Budgets activa y gasto real documentado. *(el Budget de 10 USD con avisos al 50 % y 80 % está activo; falta anotar el gasto real)*
- [ ] La dueña responde las 4 preguntas en el dashboard en menos de 5 minutos, o la limitación queda documentada.

## Riesgos que pueden mover este plan

| Riesgo | Qué hacer |
| :---- | :---- |
| El snapshot se genera en local o desde S3 | Como AWS ya tiene P3 (18/11), ambos orígenes producen lo mismo; regenerar el snapshot cada vez que cambie gold |
| PROFECO sigue dando 403 o no funciona desde AWS | Carga manual de una o dos quincenas ([ADR 0011](docs/adr/0011-ingesta-hibrida-profeco-sniim.md)); probar la descarga desde AWS |
| Mayoreo (N2) con muestra mínima (tortilla 2 filas, cilantro 1) | Marcar la comparación como aproximada y mostrar "sin dato" |
| CSV de PROFECO de 223 MB exceden memoria o tiempo de Lambda (límite del orquestador: 300 s) | Leer por partes y filtrar al leer (2.2b); si crece, Step Functions |
| ~~Inflación de alimentos no disponible~~ | Resuelto (tarea 1.7) |
| Con datos reales el snapshot revela el precio de compra | Revisar el ADR 0012 antes de publicar (redondear, mostrar solo índice o publicar con retraso) |
| Todo vive en la cuenta personal de una persona | Plantillas y script de despliegue para recrearlo en otra cuenta (ADR 0010) |
| Dependencias de cliente (A1 a A6) y aprobaciones de la dueña sin responder | Se trabaja con los supuestos provisionales y el dashboard los declara |
| El plan gratuito de AWS tiene crédito y vigencia limitados (120 USD hasta 16/05/2027) | Medir el gasto real (el Budget de 10 USD ya existe) |

## Pendientes de decidir

- **¿CD desde GitHub?** El CI (tests y lint, `.github/workflows/ci.yml`) está listo. El camino habitual para desplegar desde GitHub Actions (OIDC) **está bloqueado en esta cuenta**: la política del plan gratuito niega `iam:*Provider*` (verificado el 18/11, incluso listar proveedores). Alternativas: despliegue con CodeBuild conectado a GitHub (CodeConnections, permitido en el plan), o un script de despliegue que se ejecuta a mano. Falta decidir y registrarlo en un ADR.
- **VPC en el diagrama:** el SOW evita NAT y servidores encendidos; el diagrama dibuja una VPC y eventos de S3. Debe corregirse (tarea 5.7).
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
