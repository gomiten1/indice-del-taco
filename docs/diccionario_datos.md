# Diccionario de datos (v0, borrador)

Contrato entre capas: lo que cada tabla de **silver** y **gold** debe tener. Sirve para que quien haga silver y quien haga gold trabajen en paralelo sin esperarse. Es una v0: lo marcado como *pendiente* depende de un ADR o de una aclaración y puede cambiar.

## Convenciones

- **Semana:** semana ISO (lunes a domingo). El precio de la semana es el **último precio vigente al domingo 23:59** (aclaración A6), para tener el costo listo el lunes 9:00 (N1). Columnas `anio` y `semana_iso`; `semana_inicio` es el lunes.
- **Idempotencia:** cada tabla tiene una *llave natural*. Reprocesar una semana **reemplaza** sus filas, nunca las duplica (N6).
- **Trazabilidad:** toda fila de silver lleva `fecha_ingesta` (qué descarga la originó) y `archivo_origen`.
- **Tipos:** dinero `decimal(10,2)`, índices `decimal(12,6)`, fechas en `date`, marcas de tiempo en `timestamp` (hora de CDMX).
- **Particiones (Parquet):** `anio` y `semana_iso` para datos semanales; `anio` para datos mensuales.
- **Unidades:** se normalizan a `kg` o `pieza`. Una unidad no reconocida va a cuarentena (SOW, reglas de calidad).
- **Datos sintéticos:** lo que viene del chat, la receta y las ventas es sintético ([ADR 0007](adr/0007-datos-sinteticos-reconstruccion.md)); se identifica como tal en el dashboard.

## Bronze (datos originales, sin editar)

Ruta: `s3://<bucket-bronze>/raw/<fuente>/<detalle>/fecha_ingesta=AAAA-MM-DD/<archivo>`. Ejecutar la ingesta dos veces el mismo día escribe en la misma llave (no duplica; el bucket está versionado).

| Fuente | Ruta | Estado |
| :---- | :---- | :---- |
| Banxico SIE | `raw/banxico/SP1/fecha_ingesta=.../SP1_datos.json` y `SP1_metadatos.json` | Desplegada y probada (`src/ingesta/banxico.py`) |
| PROFECO CSV | `raw/profeco/csv/bMM_AAAA_qN.csv` | Carga manual (403 desde clientes automáticos) |
| Chat del proveedor | `raw/chat/fecha_ingesta=.../chat_proveedor.txt` | Sintético (`datos_sinteticos/`) |
| Receta y ventas | `raw/interno/receta.csv`, `raw/interno/ventas_diarias.csv` | Sintético |
| INEGI | `raw/inegi/...` | Pendiente (falta el ID del INPC) |

## Silver (Parquet limpio)

### `silver_precio_proveedor`
Origen: chat parseado por `src/ingesta/parser_chat.py`. Llave: (`fecha_hora`, `producto`).

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `fecha_hora` | timestamp | Cuándo avisó el proveedor el precio |
| `anio`, `semana_iso` | int | Partición |
| `producto` | string | `pastor`, `suadero`, `longaniza` |
| `precio_unitario` | decimal(10,2) | Pesos por `unidad` |
| `unidad` | string | `kg` o `pieza` |
| `tipo_registro` | string | `explicito`, `relativo`, `correccion`, `repetido` |
| `archivo_origen`, `linea` | string, int | Dónde está en el chat |
| `fecha_ingesta` | date | |

### `silver_precio_mercado`
Origen: PROFECO QQP (filtrado a CDMX). Llave: (`producto_original`, `presentacion`, `marca`, `nombre_comercial`, `direccion`, `fecha_registro`); hay duplicados en la fuente, la regla para resolverlos es *pendiente* (ADR).

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `fecha_registro` | date | |
| `anio`, `semana_iso` | int | Partición |
| `producto_original` | string | Como viene en PROFECO |
| `insumo` | string | Insumo del taco al que equivale; nulo si no aplica |
| `equivalencia` | string | `exacta` o `proxy` (pastor → pierna de cerdo; suadero → corte de res). *Pendiente* aprobar con la dueña |
| `presentacion`, `marca` | string | |
| `precio` | decimal(10,2) | Pesos por presentación |
| `precio_kg` | decimal(10,2) | Normalizado; nulo si no se puede convertir |
| `canal` | string | `mayoreo` si `giro = Central de Abasto`, si no `menudeo` |
| `cadena_comercial`, `nombre_comercial`, `municipio` | string | |
| `archivo_origen` | string | `bMM_AAAA_qN.csv` |
| `fecha_ingesta` | date | |

### `silver_inpc`
Origen: Banxico (`SP1`, INPC general). Llave: (`serie_id`, `fecha`). Partición: `anio`.

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `serie_id` | string | `SP1` (general). La serie de alimentos es *pendiente* (tarea 1.7) |
| `fecha` | date | Primer día del mes |
| `indice` | decimal(12,6) | Valor del índice (Banxico lo entrega como texto) |
| `fecha_ingesta` | date | |

### `silver_receta`
| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `tipo_taco` | string | `suadero` o `pastor` |
| `insumo` | string | Hoy solo la carne; tortilla, verduras y salsa son *pendientes* (sin dato del cliente) |
| `gramos_por_taco` | int | 55 (suadero), 50 (pastor) según A2 |
| `vigente_desde` | date | |

### `silver_ventas_diarias`
Dato de apoyo; no entra al índice. Llave: `fecha`.

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `fecha` | date | |
| `tacos` | int | |

### `cuarentena`
Todo lo que no pasa las reglas de calidad. Se guarda en su propio bucket.

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `fuente` | string | `chat`, `profeco`, `banxico` |
| `regla` | string | `precio_invalido`, `fecha_invalida`, `unidad_desconocida`, `cambio_relativo_sin_base`, `esquema`, etc. |
| `motivo` | string | Detalle legible |
| `registro_original` | string | La fila o mensaje tal cual |
| `archivo_origen`, `linea` | string, int | |
| `ejecucion_id`, `fecha_ingesta` | string, date | |

### `registro_ejecuciones`
Una fila por etapa y fuente en cada corrida (E5).

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `ejecucion_id` | string | |
| `fecha_hora_inicio` | timestamp | |
| `etapa` | string | `ingesta`, `silver`, `gold` |
| `fuente` | string | |
| `registros_leidos`, `aceptados`, `rechazados` | int | |
| `duracion_s` | decimal(8,2) | |
| `estado` | string | `ok`, `sospechoso`, `error` |

## Gold (tablas de negocio, una por pregunta)

Costo por taco = Σ (`gramos_por_taco` / 1000 × `precio_kg` del insumo). Índice = costo de la semana / costo de la semana base × 100.

### `costo_taco_semanal` (P1)
Llave: (`anio`, `semana_iso`, `tipo_taco`, `incluye_merma`). **Pública.**

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `anio`, `semana_iso`, `semana_inicio` | int, int, date | |
| `tipo_taco` | string | `suadero` o `pastor` |
| `costo_taco_mxn` | decimal(8,2) | Pesos por taco (lo pide N1) |
| `indice_base100` | decimal(8,2) | Base 100 en `semana_base` |
| `semana_base` | date | Primera semana con todos los insumos con dato ([ADR 0009](adr/0009-semana-base-indice.md)) |
| `incluye_merma` | boolean | Versión con merma solo para pastor ([ADR 0008](adr/0008-merma.md)) |
| `insumos_con_dato` | int | Cuántos insumos de la receta tenían precio esa semana (completitud) |

### `precio_insumo_semanal` (P1, P3)
Llave: (`anio`, `semana_iso`, `insumo`, `fuente`). Las filas con `fuente = 'proveedor'` son **privadas**.

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `anio`, `semana_iso` | int | |
| `insumo` | string | |
| `fuente` | string | `proveedor`, `menudeo`, `mayoreo` |
| `precio_kg` | decimal(10,2) | |
| `n_observaciones` | int | Cuántos precios se usaron |
| `estadistico` | string | `mediana` ([ADR 0003](adr/0003-estadistico-precio-semanal.md)) |

### `comparativo_proveedor` (P2)
Llave: (`anio`, `semana_iso`, `insumo`).

| Columna | Tipo | Descripción | Pública |
| :---- | :---- | :---- | :---- |
| `anio`, `semana_iso`, `insumo` | | | Sí |
| `precio_proveedor_kg` | decimal(10,2) | Precio de compra exacto | **No** |
| `precio_menudeo_kg`, `precio_mayoreo_kg` | decimal(10,2) | Referencia de mercado | Sí |
| `brecha_menudeo_pct`, `brecha_mayoreo_pct` | decimal(8,2) | (proveedor / mercado − 1) × 100 | Sí |
| `aproximado` | boolean | Verdadero si el insumo usa un proxy | Sí |

### `comparativo_inflacion` (P4)
Llave: (`anio`, `mes`). Mensual por la frecuencia del INPC. **Pública.**

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `anio`, `mes` | int | |
| `indice_taco_base100` | decimal(8,2) | Índice del taco, mensualizado |
| `inpc_general_base100` | decimal(8,2) | Misma base 100 |
| `inpc_alimentos_base100` | decimal(8,2) | Nulo hasta resolver la serie de alimentos (tarea 1.7) |
| `base_mes` | date | Mes que vale 100 |

### `contribucion_insumo` (P3)
Llave: (`trimestre`, `tipo_taco`, `insumo`). **Pública.**

| Columna | Tipo | Descripción |
| :---- | :---- | :---- |
| `trimestre` | string | `2026Q3` |
| `tipo_taco` | string | |
| `insumo` | string | |
| `aportacion_mxn` | decimal(8,2) | Cuánto subió el costo por taco por este insumo |
| `aportacion_pct` | decimal(8,2) | Parte del cambio total |
| `ranking` | int | 1 = el que más aportó; el dashboard muestra los 3 primeros |

## Snapshot público

El snapshot que lee el dashboard excluye `precio_proveedor_kg` y las filas de `precio_insumo_semanal` con `fuente = 'proveedor'`. Todo lo demás de gold se publica.

## Pendientes que cambian este contrato

| Qué | Dónde se decide |
| :---- | :---- |
| Confirmar con la dueña la semana base y la merma | Aclaración pregunta 5 y A5 (decididos provisionalmente en los ADR 0009 y 0008) |
| Costo de la salsa | Aclaración pregunta 3 (excluida por ahora, [ADR 0005](adr/0005-salsa.md)) |
| Regla para duplicados de PROFECO y equivalencias de cortes | ADR de proxies (ver `fuentes.md`) |
| Serie de inflación de alimentos | Tarea 1.7 del roadmap |
| Insumos de la receta además de la carne | Aclaración, pregunta 1 y 3 |
