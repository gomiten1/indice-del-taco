# Parquet contra CSV: bytes escaneados en Athena

Evidencia del criterio de aceptación de E3 («comparación documentada de bytes escaneados CSV vs. Parquet»). Medido el 18/11/2026 en la
cuenta del proyecto (`us-east-2`, workgroup `indice-del-taco-dev`).

## Qué se midió y por qué así

Los datos reales del proyecto son diminutos (unos KB), y con eso la diferencia entre formatos no se puede apreciar. Para que la
comparación signifique algo se generó un archivo **sintético con el mismo esquema de PROFECO** (15 columnas, 200,000 filas, semilla fija)
y se guardó dos veces en S3: como CSV y como Parquet (compresión Snappy). Se crearon dos tablas externas, se corrieron las mismas
consultas y se leyó `DataScannedInBytes` de cada una. Al terminar se borraron las tablas, la base de datos y los archivos.

| | CSV | Parquet |
| :---- | ----: | ----: |
| Tamaño del archivo | 42.1 MB | 5.6 MB (7.5 veces menos) |

## Resultados

| Consulta | CSV | Parquet | Reducción |
| :---- | ----: | ----: | ----: |
| A. Precio medio por producto, solo CDMX (usa 3 de 15 columnas) | 44,094,437 B | 723,543 B | **98.4 %** (61 veces menos) |
| B. Contar todas las filas | 44,094,437 B | 0 B | **100 %** (se responde con los metadatos) |
| C. Precio máximo (usa 1 de 15 columnas) | 44,094,437 B | 418,792 B | **99.1 %** (105 veces menos) |

Las respuestas fueron **idénticas** en ambos formatos (por ejemplo, 200,000 filas y precio máximo 659.73).

## Por qué pasa

- **CSV:** Athena tiene que leer el archivo completo, sin importar cuántas columnas pida la consulta: siempre 44 MB.
- **Parquet:** guarda los datos por columna, así que solo lee las columnas que la consulta usa, y además comprime. El conteo no lee datos,
  solo los metadatos del archivo.

## Qué significa para el proyecto

- **Costo:** Athena cobra por dato escaneado (precio público ≈ US$ 5 por TB, con un mínimo de 10 MB por consulta; no se verificó en la
  cuenta). Con los volúmenes de este proyecto el costo es despreciable en ambos casos; lo importante es que no crece con el número de columnas.
- **El tope del workgroup:** `indice-del-taco-dev` corta cualquier consulta que escanee más de 100 MB. Un CSV de PROFECO real (≈ 223 MB por
  quincena) **no se podría consultar** en Athena; convertido a Parquet en silver sí, y barato. Es la razón de la arquitectura de capas ([ADR 0002](adr/0002-capas-parquet-catalogo.md)).

## Limitaciones

- Los datos son **sintéticos y aleatorios**: la compresión real de PROFECO puede ser mejor o peor. Debe repetirse con una quincena real
  cuando se cargue (un CSV real pesa ≈ 300 bytes por fila; el de prueba ≈ 210).
- Un solo archivo de 200,000 filas: con muchas particiones pequeñas, Parquet también paga el costo de leer el pie de cada archivo
  (por eso el silver del proyecto, con archivos de pocas filas, no muestra ventaja hoy).
- Se midió una vez por consulta; los bytes escaneados son deterministas, los tiempos no (0.5 a 1.1 s en todas).

## Cómo repetirlo

```sql
-- CSV: todas las columnas como texto (OpenCSVSerde) y se convierte al consultar
CREATE EXTERNAL TABLE precios_csv (producto string, presentacion string, marca string, categoria string, catalogo string,
  precio string, fecha_registro string, cadena_comercial string, giro string, nombre_comercial string, direccion string,
  estado string, municipio string, latitud string, longitud string)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde' STORED AS TEXTFILE
LOCATION 's3://<bucket>/experimento-formato/csv/' TBLPROPERTIES ('skip.header.line.count'='1');

-- Parquet: los mismos campos, con tipos (precio, latitud y longitud double; fecha_registro date)
CREATE EXTERNAL TABLE precios_parquet (...) STORED AS PARQUET LOCATION 's3://<bucket>/experimento-formato/parquet/';

SELECT producto, round(avg(CAST(precio AS double)), 2) FROM precios_csv     WHERE estado = 'Ciudad de México' GROUP BY producto;
SELECT producto, round(avg(precio), 2)                 FROM precios_parquet WHERE estado = 'Ciudad de México' GROUP BY producto;
```
