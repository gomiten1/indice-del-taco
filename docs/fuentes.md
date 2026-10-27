# Fuentes de datos (capa bronce)

Resultado de la revisión de fuentes para la ingesta (H0/H2). Las pruebas se hicieron el 24 y 25 de octubre de 2026, con pocas peticiones y respetando los límites de cada servicio. Cada afirmación dice si fue **probada** o **no verificada**.

| Fuente | Qué aporta | Token | Frecuencia observada | Automatizable | Estado |
|---|---|---|---|---|---|
| PROFECO QQP | Precios al menudeo, más algo de Central de Abasto | No | Quincenal por archivo, con huecos y retraso | Solo la detección. La descarga da 403 | Esquema base del proyecto |
| Banxico SIE | INPC general | Sí | Mensual | Sí | Probada |
| INEGI | INPC, contraste contra Banxico | Sí | Quincenal y mensual (según el SOW, no verificado) | Sí, falta el ID | Token probado, ID pendiente |
| SNIIM | Mayoreo | No | Diaria, según su sitio (no verificado) | No | Descartada |

## PROFECO: Quién es Quién en los Precios

- **Dataset:** "Programa Quién es quién en los precios (2026)", con versiones para 2024 y 2025. Slugs: `programa_quien_es_quien_precios_2024`, `_2025` y `_2026`.
  - Página: https://www.datos.gob.mx/dataset/programa_quien_es_quien_precios_2026
  - Metadatos por API (CKAN, responde sin problema): `https://www.datos.gob.mx/api/3/action/package_show?id=programa_quien_es_quien_precios_2026`
- **Archivos:** un CSV por quincena, con nombre `bMM_AAAA_qN.csv` (por ejemplo `b07_2026_q2.csv`). El dataset de 2026 listaba 9 CSV; el más reciente era julio q2. Aparentan faltar febrero q1, marzo y abril (no verificado archivo por archivo).
- **URL de descarga:** `https://repodatos.atdt.gob.mx/api_update/profeco/programa_quien_es_quien_precios_2026/b07_2026_q2.csv`
- **Descarga manual:** abrir la página del dataset en el navegador y bajar el CSV de la quincena deseada desde ahí. Con `curl` el servidor devuelve **403 Access Denied** (CDN Akamai, protección contra clientes automáticos). Se probó con dos archivos y con distintos `User-Agent`. No se probó desde AWS.
- **Actualización:** el dataset de 2026 se modificó por última vez el 22/09/2026. No hay frecuencia oficial documentada.

### Esquema (tomado de `b07_2026_q2.csv`)

Los tipos se infieren de la muestra; no hay diccionario de datos oficial.

| Columna | Tipo | Ejemplo |
|---|---|---|
| `producto` | texto | Acelga |
| `presentacion` | texto | Manojo |
| `marca` | texto | S/M |
| `categoria` | texto | Hortalizas Frescas |
| `catalogo` | texto | Frutas y Legumbres |
| `precio` | decimal | 20.0 |
| `fecha_registro` | fecha (`AAAA-MM-DD`) | 2026-07-16 |
| `cadena_comercial` | texto | Central de Abasto |
| `giro` | texto | Central de Abasto |
| `nombre_comercial` | texto | Central de Abasto |
| `direccion` | texto | Av. Mahatma Gandhi S/N… |
| `estado` | texto | Aguascalientes |
| `municipio` | texto | Aguascalientes |
| `latitud` | decimal | 21.832072 |
| `longitud` | decimal | -102.292976 |

### Lo que se observó en `b07_2026_q2.csv`

- **Tamaño y formato:** 223.5 MB, 744,623 filas, UTF-8 **con BOM** (el primer encabezado llega como `﻿producto` si no se maneja).
- **Cobertura:** del 16 al 31 de julio de 2026 (15 días), 29 estados. CDMX tiene 157,076 filas (21%).
- **Calidad:** los 744,623 precios son numéricos.
- **Duplicados:** hay 11,438 combinaciones de (producto, presentación, marca, establecimiento, dirección, fecha) repetidas. No se puede asumir una fila por producto, tienda y día; plata tiene que decidir cómo resolverlo.
- **Para el taco, solo CDMX:**

| Insumo | Observación | Muestra |
|---|---|---|
| Pastor | No hay "pastor". Proxy: pierna de cerdo sin hueso o pernil | 115 registros, mediana $108/kg |
| Suadero | No aparece. Proxy: cortes de res como falda (mediana unos $231/kg en la revisión) | Por documentar en un ADR |
| Tortilla de maíz | Mediana unos $14.5/kg | Ver nota de Central de Abasto |
| Cebolla, limón, cilantro, piña | Medianas aproximadas: $34.9/kg, $32–35/kg, $10/manojo, $25/kg | Sin recalcular en esta versión |

- **Central de Abasto de CDMX** (`giro = Central de Abasto`): 1,289 filas, 136 productos. Para el taco: carne de cerdo 22, carne de res 22, cebolla 12, limón 10, tortilla 2, cilantro 1. Es la única referencia de mayoreo que tenemos y la muestra es pequeña.

### Riesgos para bronce

1. **Descarga automática bloqueada (403).** Propuesta: la Lambda consulta el CKAN, detecta el archivo nuevo y avisa; la carga a bronce es manual con un script. Si desde AWS sí pasa, se pasa a ingesta completa. Va a un ADR.
2. **Tamaño.** 223 MB por quincena. Bronce guarda el archivo tal cual; el filtro de CDMX y de columnas se hace en plata, leyendo por partes.
3. **Idempotencia.** La llave natural es el nombre del archivo (`bMM_AAAA_qN`).
4. **Huecos y retraso.** El corte semanal no aplica a esta fuente; la regla de completitud debe contarlo.
5. **No usar la copia de datamx.io.** Su metadato dice 2019 y está desactualizada.

## Banxico SIE (INPC)

- **Token:** gratis, de 64 caracteres. Se envía en el header `Bmx-Token` y se guarda en Parameter Store. Variable local: `BANXICO_TOKEN`.
- **Serie:** `SP1` = INPC general, mensual, desde 1969. Último dato probado: 01/09/2026 = 146.075.
- **Endpoints probados:**
  - Dato más reciente: `https://www.banxico.org.mx/SieAPIRest/service/v1/series/SP1/datos/oportuno`
  - Metadatos: `https://www.banxico.org.mx/SieAPIRest/service/v1/series/SP1`
- **Límites** (https://www.banxico.org.mx/SieAPIRest/service/v1/doc/limiteConsultas):
  - Oportunas: 80 por minuto y 40,000 por día.
  - Históricas (rango de fechas): 200 por 5 minutos y 10,000 por día.
  - Si se excede, devuelve HTTP 400 con `secondsToReset`. Esto sale de la documentación, no se provocó.
  - Recomendación oficial: guardar los resultados. Bronce cumple ese papel.
- **No verificado:** consulta por rango de fechas, series de subíndices de alimentos y la "Salvedad de uso" del API (no se pudo abrir).

## INEGI (INPC)

- **Token:** gratis con registro. Variable local: `INEGI_TOKEN`.
- **Guía oficial:** https://www.inegi.org.mx/servicios/api_indicadores.html
- **Formato de la consulta (probado con otros indicadores):**
  `https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{IDs separados por coma}/es/00/true/BISE/2.0/{TOKEN}?type=json`
- **Probado:** el token funciona con población total (`1002000001`) y con `6207024011,6207024012`.
- **Pendiente: el ID del INPC.**
  - Los IDs `216064`, `628194` y `737121` no existen.
  - El catálogo `CL_INDICATOR` responde "No autorizado" (error 110), así que no se pueden listar indicadores por API.
  - El ID se saca con el **Constructor de consultas**, que es una sección de la misma guía oficial (https://www.inegi.org.mx/servicios/api_indicadores.html). Hay que elegir a mano cada campo (indicador, geografía, etc.) y al final devuelve la clave. Es tedioso, pero se hace una sola vez. Anotar aquí el ID cuando alguien lo obtenga: `ID_INPC = ______`.
  - Si no se consigue, el proyecto puede apoyarse solo en Banxico y anotarlo como limitación.
- **Límites:** no hay cifras publicadas. Se asume un trato similar al de Banxico.

## SNIIM (descartada)

- Solo abre el menú: https://www.economia-sniim.gob.mx/analisis/Precios.asp (HTTP 200).
- Las páginas de consulta (Porcinos, Bovinos, Frutas y Hortalizas, entre otras) dieron 404, 403 o 503, tanto con mi cliente como en el navegador. No se encontró una consulta que funcione y no hay opción de descarga ni API visible.
- **Decisión:** no se usa SNIIM. El mayoreo se toma de las filas de Central de Abasto del CSV de PROFECO (ver arriba). Va a un ADR.

## Otras fuentes revisadas

- **datos.gob.mx, grupo Agricultura (85 datasets):** se revisaron solo los títulos. Son sanitarios de SENASICA, créditos de FIRA y azúcar de CONADESUCA. No hay precios de mayoreo.
- **SIAP, "Cosechando Números del Campo":** aparece como fuente oficial. No se revisó a fondo.
- **Chat de WhatsApp del proveedor:** es un `.txt` sintético y no se revisó en esta ronda.

## Pendientes

- [ ] ID del INPC en INEGI (Constructor de consultas).
- [ ] Bajar otra quincena de PROFECO y confirmar que el esquema es el mismo.
- [ ] Probar la descarga de PROFECO desde AWS.
- [ ] Probar Banxico por rango de fechas.
- [ ] ADRs: ingesta híbrida de PROFECO, frecuencia por fuente, descarte de SNIIM, proxies de pastor y suadero.
