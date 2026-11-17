# ADR 0006: Visualización pública en Streamlit sobre snapshot sanitizado

* **Estado:** Aceptado
* **Fecha:** 2026-11-16
* **Autores:** Equipo Data Solutions — La TaquerIA Opus

## Contexto
La dueña de *La TaquerIA Opus* necesita responder cuatro preguntas clave de costos en menos de 5 minutos sin abrir consolas técnicas de AWS, mientras que el SOW §8 prohíbe exponer en el tablero público los precios exactos pagados a su proveedor.

## Decisión
1. Desarrollar el tablero interactivo en **Python con Streamlit** (`dashboard/app.py`), desplegable en Streamlit Community Cloud sin costo de servidores encendidos.
2. Desacoplar el tablero de los buckets privados mediante un **snapshot sanitizado** (`snapshot_gold/`), que contiene únicamente índices base 100, costos unitarios agregados por taco, brechas porcentuales frente al mercado y comparativos contra el INPC, omitiendo la columna de precio unitario exacto del proveedor.
3. Declarar explícitamente en el tablero los supuestos metodológicos (gramajes de receta, merma del 12 % solo en pastor y aproximaciones de mercado CDMX).

## Consecuencias
* **Positivas:** Cumplimiento estricto de confidencialidad de precios, cero costo de hosting y respuesta visual inmediata a las preguntas P1–P4.
* **Negativas:** Requiere actualizar `snapshot_gold/` al cierre de cada corte semanal publicado.