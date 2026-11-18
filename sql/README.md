# Consultas SQL (Athena)

Base de datos `indice_taco_dev`, workgroup `indice-del-taco-dev` (tope de 100 MB escaneados por consulta). Las tablas
se declaran en `infra/06-glue-athena.yaml` (DDL manual, sin crawlers; las particiones se deducen de la ruta).

> **Los números de abajo salen de datos sintéticos** (chat del proveedor, receta) y del INPC real de Banxico. Cuenta solo la
> carne de cada taco (ADR 0005). Se leen como una demostración de que el pipeline funciona, no como cifras de la taquería.

## P1: ¿Cuánto cuesta hoy cada taco? (`p1_costo_actual.sql`)

| tipo_taco | semana_inicio | costo_taco_mxn | indice_base100 |
| :---- | :---- | ----: | ----: |
| pastor | 2026-09-21 | 7.75 | 112.32 |
| suadero | 2026-09-21 | 10.18 | 112.12 |

**Lectura:** en la última semana, la carne de un taco de pastor cuesta $7.75 y la de suadero $10.18. Frente a la semana base
(enero) ambos están ~12 % más caros, y coincide con el alza de ≈12 % del proveedor que muestra el chat (aclaración A1).

## P4: ¿Sube más o menos que la inflación? (`p4_vs_inflacion.sql`)

| mes | índice del taco | INPC general | brecha (pp) |
| ----: | ----: | ----: | ----: |
| ene | 100.00 | 100.00 | 0.00 |
| mar | 100.72 | 101.36 | -0.64 |
| abr | 108.70 | 101.56 | +7.13 |
| sep | 112.32 | 101.73 | +10.59 |

**Lectura:** de enero a septiembre la carne del pastor subió ~12.3 % y el INPC general ~1.7 %, así que el taco se encareció
~10.6 puntos más que la inflación. El salto está en abril (+8 % en un mes). Esto **no** respalda el "30 %" que menciona la
dueña (A1): el dato del proveedor da ≈12 %.

## P3: ¿Qué insumo explica el aumento de costos? (`p3_contribucion.sql`)

Trimestre 2026Q3 (último con datos):

| tipo_taco | ranking | insumo | aportación ($ por taco) | aportación (%) | estado |
| :---- | ----: | :---- | ----: | ----: | :---- |
| pastor | 1 | pastor | 0.10 | 100.00 | ok |
| pastor | 2 a 6 | tortilla, cebolla, cilantro, limón, piña | | | sin dato |
| suadero | 1 | suadero | 0.61 | 100.00 | ok |
| suadero | 2 a 5 | tortilla, cebolla, cilantro, limón | | | sin dato |

**Lectura:** en el tercer trimestre la carne subió $0.10 por taco de pastor y $0.61 por taco de suadero. Hoy la carne aparece con 100 %
solo porque **es el único insumo con precio**; los demás figuran como «sin dato» (no como 0 %) hasta que haya precios de mercado (PROFECO).
Escanea menos de 1 KB.

## Pendientes
- **P2** (proveedor contra el mercado) necesita los precios de PROFECO, y **P3** solo será informativa con más de un insumo.
- La inflación de alimentos (N4) falta: hay que encontrar la serie (tarea 1.7 del roadmap).
