# ADR 0011: Ingesta híbrida de PROFECO y exclusión de SNIIM

* **Estado:** Aceptado
* **Fecha:** 2026-11-16
* **Autores:** Equipo Data Solutions — La TaquerIA Opus

## Contexto
Durante las pruebas de extracción automatizada, los portales de descarga masiva de PROFECO (*Quién es Quién en los Precios*) devolvieron bloqueos HTTP `403 Forbidden` a peticiones automatizadas desde Lambda, y los archivos quincenales completos superan los 220 MB. Asimismo, el portal SNIIM presenta indisponibilidad intermitente y cobertura limitada para cortes específicos de taquería.

## Decisión
1. **Ingesta híbrida para PROFECO:** Descargar manualmente las quincenas relevantes de Ciudad de México y cargar los archivos crudos en `bronze` bajo el prefijo particionado `raw/profeco/quincena=bMM_AAAA_qN/`, procesándolos por bloques (*chunking*) en la capa Silver para deduplicar registros repetidos sin exceder la memoria de Lambda.
2. **Descarte de SNIIM y uso de proxies CDMX:** Sustituir SNIIM por referencias de menudeo y Central de Abasto CDMX de PROFECO mediante proxies documentados para carne de suadero y pastor, marcando los comparativos P2 y P3 como *aproximados* en Gold y en el tablero.

## Consecuencias
* **Positivas:** Elimina fallos por bloqueo WAF/403 en las corridas semanales desatendidas y mantiene la trazabilidad en Bronze.
* **Negativas:** La actualización de precios de referencia de mercado depende de cargas quincenales manuales en Bronze.