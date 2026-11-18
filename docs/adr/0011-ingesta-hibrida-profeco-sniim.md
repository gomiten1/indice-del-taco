# ADR 0011: Ingesta híbrida de PROFECO y exclusión de SNIIM

* **Estado:** Aceptado (la carga y el silver de PROFECO **aún no están implementados**)
* **Fecha:** 2026-11-16
* **Autores:** Equipo Data Solutions — La TaquerIA Opus

## Contexto
El 14/11/2026 los 55 CSV de PROFECO (*Quién es Quién en los Precios*) devolvieron `403` (protección Akamai) a peticiones automatizadas con `curl` desde una máquina local (`fuentes.md`). **No se ha probado desde AWS** (Lambda). Cada archivo quincenal pesa unos 220 MB. SNIIM, por su parte, no ofrece descarga ni API: solo abre el menú y las páginas de consulta dieron 404, 403 o 503.

## Decisión
1. **Ingesta híbrida para PROFECO:** Descargar manualmente las quincenas relevantes de Ciudad de México y cargar los archivos crudos en `bronze` como `raw/profeco/csv/bMM_AAAA_qN.csv` (el nombre del archivo es la llave natural, como en el diccionario de datos), para procesarlos por bloques (*chunking*) en la capa Silver para deduplicar registros repetidos sin exceder la memoria de Lambda.
2. **Descarte de SNIIM y uso de proxies CDMX:** Sustituir SNIIM por referencias de menudeo y Central de Abasto CDMX de PROFECO mediante proxies documentados para carne de suadero y pastor, marcando los comparativos P2 y P3 como *aproximados* en Gold y en el tablero.

## Consecuencias
* **Positivas:** Evita depender de una descarga automática bloqueada en las corridas semanales desatendidas y mantiene la trazabilidad en Bronze.
* **Negativas:** La actualización de precios de referencia de mercado depende de cargas quincenales manuales en Bronze.
* **Pendiente:** probar la descarga desde AWS; si funcionara, se pasaría a ingesta automática.
