# ADR 0002: Arquitectura Medallion, formato Parquet y catálogo en AWS Glue

* **Estado:** Aceptado
* **Fecha:** 2026-11-16
* **Autores:** Equipo Data Solutions — La TaquerIA Opus

## Contexto
El pipeline ingesta fuentes heterogéneas (mensajes de texto de WhatsApp, series JSON de Banxico y archivos tabulares de receta/PROFECO) y requiere consultas analíticas periódicas en Amazon Athena con bajo costo de escaneo y trazabilidad completa ante errores de captura.

## Decisión
1. **Arquitectura Medallion en cuatro buckets independientes:**
   * `bronze`: datos crudos inmutables particionados por `fecha_ingesta=AAAA-MM-DD/` con versionado S3 habilitado.
   * `silver`: datos limpios, normalizados y tipados, particionados por `anio` y `semana_iso`.
   * `gold`: tablas agregadas de negocio listas para consumo analítico y tablero público.
   * `cuarentena`: registros rechazados por reglas de calidad con motivo explícito, sin detener el flujo de registros válidos.
2. **Formato columnar Apache Parquet con compresión Snappy** en las capas `silver` y `gold` para reducir el volumen escaneado por consulta.
3. **Catálogo en AWS Glue Data Catalog con Partition Projection** habilitado en Athena (`workgroup` con tope de 100 MB por consulta) para evitar costos de crawlers periódicos y eliminar la necesidad de ejecutar `MSCK REPAIR TABLE`.

## Consecuencias
* **Positivas:** Escaneo menor a 1 KB por consulta analítica en Athena, aislamiento de datos corruptos en cuarentena y cero mantenimiento de particiones manuales.
* **Negativas:** Requiere incluir la capa administrada *AWS SDK for pandas* (`pyarrow`) en las funciones Lambda de transformación.