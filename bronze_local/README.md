# bronze_local/ — snapshot local de la capa bronze

Esta carpeta guarda la **primera ingesta local manual** de las tres fuentes
del proyecto, hecha antes de montar las Lambdas en AWS. Todos los archivos
están **tal cual los devolvió cada servidor** (bronze = crudo, sin
transformar). Cada nombre lleva `fecha_ingesta` al final para que una nueva
descarga no pise la anterior.

Cuando esté desplegado el bucket bronze en S3, este contenido se sube ahí
(o se regenera desde una Lambda) y esta carpeta pasa a ser solo histórica.

## Contenido

| Ruta | Qué es | Fuente | Fecha de ingesta | Bytes |
|---|---|---|---|---|
| `banxico/SP1/SP1_datos_2026-11-14.json`          | INPC general mensual, serie histórica completa (ene-1969 a oct-2026, 694 observaciones) | Banxico SIE | 2026-11-14 | 33,323 |
| `banxico/SP1/SP1_metadatos_2026-11-14.json`      | Metadatos de la serie SP1 (periodicidad, unidad, rango de fechas)                       | Banxico SIE | 2026-11-14 |    302 |
| `profeco/ckan/package_show_2024_2026-11-14.json` | Metadata CKAN del dataset `programa_quien_es_quien_precios_2024` (24 CSV)               | datos.gob.mx | 2026-11-14 | 38,087 |
| `profeco/ckan/package_show_2025_2026-11-14.json` | Metadata CKAN del dataset `_2025` (22 CSV)                                              | datos.gob.mx | 2026-11-14 | 35,430 |
| `profeco/ckan/package_show_2026_2026-11-14.json` | Metadata CKAN del dataset `_2026` (9 CSV, el más reciente `b07_2026_q2.csv`)            | datos.gob.mx | 2026-11-14 | 17,508 |
| `profeco/csv/intentos_2026-11-14.tsv`            | Log de HEAD a los 55 CSV listados por CKAN: **55/55 devolvieron 403 Akamai**            | - | 2026-11-14 | 1,637 |
| `inegi/catalogo/CL_INDICATOR_2026-11-14.json`    | Catálogo completo de indicadores BISE (32,314 entradas)                                 | INEGI API | 2026-11-14 | 3,858,975 |
| `inegi/catalogo/CL_TOPIC_2026-11-14.json`        | Catálogo de temas (242 entradas; **INPC = tema `0137`**)                                | INEGI API | 2026-11-14 | 14,033 |
| `inegi/indicator/1002000001_2026-11-14.json`     | Muestra `INDICATOR/1002000001` (población total) — confirma que el token funciona       | INEGI API | 2026-11-14 | 2,758 |

## Resumen de la ingesta (al 14/11/2026)

- **Banxico SIE:** ✅ funciona completo. Serie `SP1` descargable con token en header `Bmx-Token`.
  Última lectura: **01/10/2026 = 147.026** (mensual).
- **PROFECO CKAN (metadata):** ✅ funciona. Endpoint correcto:
  `https://www.datos.gob.mx/api/3/action/package_show?id=programa_quien_es_quien_precios_<anio>`.
  Da la lista de los CSV, sus URLs y sus hashes.
- **PROFECO CSV (archivos):** ❌ bloqueado. **Los 55 CSV listados (2024+2025+2026)
  devuelven 403 Akamai** al intentar `GET` o `HEAD` con `curl`. Pendiente
  definir en ADR si se pasa a ingesta híbrida (bajada manual) o si se
  prueba desde Lambda AWS (otra IP).
- **INEGI:** ✅ token funciona. Tema del INPC = `0137`. Se descubrió que
  `CL_INDICATOR/null` lista los 32,314 indicadores en un solo JSON
  (3.86 MB) — útil para rastrear el ID del INPC general en frío,
  sin golpear el API más veces.

## Cómo regenerar esta ingesta

Los comandos usados (resumidos) son:

```bash
# Banxico SP1 completo
curl -H "Bmx-Token: $BANXICO_TOKEN" \
  "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SP1/datos" \
  -o banxico/SP1/SP1_datos_$(date +%Y-%m-%d).json
```

```bash
# PROFECO CKAN, por año
curl -L "https://www.datos.gob.mx/api/3/action/package_show?id=programa_quien_es_quien_precios_2026" \
  -o profeco/ckan/package_show_2026_$(date +%Y-%m-%d).json
```

```bash
# INEGI catalogo completo
curl "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/CL_INDICATOR/null/es/BISE/2.0/$INEGI_TOKEN?type=json" \
  -o inegi/catalogo/CL_INDICATOR_$(date +%Y-%m-%d).json
```

En la siguiente ronda esto se mete a un script en `src/ingesta/` o,
mejor, al handler de la Lambda de `infra/02-lambda.yaml`.
