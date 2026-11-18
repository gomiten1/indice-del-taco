# ADR 0020: PROFECO entra por el CSV descargado a mano y se registra hasta qué día llegan los datos

**Estado:** Aceptada
**Fecha:** 2026-11-18

## Contexto

La descarga automática de PROFECO está bloqueada ([ADR 0011](0011-ingesta-hibrida-profeco-sniim.md)). Ya tenemos un archivo real, `b07_2026_q2.csv` (≈ 220 MB, 744,623 filas, todo el país), bajado a mano del portal de datos abiertos.
Cubre **del 16 al 31 de julio de 2026**; en CDMX son 157,076 filas. El pipeline corre cada lunes, pero el CSV no se actualiza solo.

## Decisión

1. **La fuente de PROFECO es el CSV descargado a mano** y subido a bronze (`raw/profeco/…`). No se inventan ni se rellenan semanas que el archivo no cubre.
2. **Se registra la cobertura real.** Cada corrida de silver calcula `fecha_min` y `fecha_max` de las filas **que sí se usan** (CDMX y solo los insumos del taco), no del archivo completo, y las guarda en su resumen (`registro_ejecuciones`).
   Hoy: **16/07/2026 a 31/07/2026**.
3. **Transparencia:** todo lo que se publique con datos de PROFECO (P2, P3, tablero) debe decir hasta qué fecha llegan. Las semanas sin dato de mercado salen como «sin dato» ([ADR 0019](0019-datos-faltantes-sin-dato.md)), nunca como cero ni arrastrando un precio viejo.
4. **Cuando haya un CSV nuevo** basta subirlo con otra `fecha_ingesta`; silver combina todos los archivos y deduplica los días que se traslapen.

## Razón

Es el único dato real de mercado que tenemos y es oficial. Decir hasta dónde llega evita que parezca que la comparación está al día cuando solo cubre dos semanas.

## Consecuencias

- P2 y P3 con mercado solo tienen datos en las semanas ISO 29 a 31 de 2026 hasta que se cargue más.
- Alguien debe subir el CSV de cada quincena; si pasan más de ~2 meses, conviene alertarlo (pendiente).
- Equivalencias y reglas de calidad: [ADR 0015](0015-proxies-pastor-y-suadero.md) y [ADR 0021](0021-reglas-silver-profeco.md).
