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

Índice del taco de pastor (base 100 en enero) contra tres referencias de Banxico, con la misma base:

| mes | taco | INPC general | alimentos | pecuarios | brecha contra el INPC (pp) |
| ----: | ----: | ----: | ----: | ----: | ----: |
| ene | 100.00 | 100.00 | 100.00 | 100.00 | 0.00 |
| mar | 100.72 | 101.36 | 100.71 | 99.19 | -0.64 |
| abr | 108.70 | 101.56 | 100.89 | 98.02 | +7.13 |
| jul | 110.87 | 101.10 | 101.69 | 96.28 | +9.77 |
| sep | 112.32 | 101.73 | 101.97 | 97.41 | +10.59 |

**Lectura:** de enero a septiembre la carne del taco de pastor subió ~12.3 %, mientras el INPC general subió ~1.7 %, los **alimentos procesados** ~2.0 % y los **pecuarios** *bajaron* ~2.6 %.
El taco se encareció unos 10.6 puntos más que la inflación general, y mucho más que los alimentos. El salto está en abril (+8 % en un mes).
Esto **no** respalda el «30 %» que menciona la dueña (A1): el dato del proveedor da ≈ 12 %.

**Cómo leer las dos columnas nuevas:** «Alimentos» (`SP66540`) es del índice *subyacente*: productos procesados, **sin** frutas, verduras ni carne fresca.
«Pecuarios» (`SP56386`) es *no subyacente*, más volátil. Ninguna es «toda la comida». Si una serie falta, su columna sale vacía (sin dato), nunca en cero.

## P2: ¿El proveedor cobra caro o barato frente al mercado? (`p2_proveedor_vs_mercado.sql`)

PROFECO (CSV de julio, **solo 16 al 31 de julio de 2026**: semanas 29 a 31). Brecha del proveedor contra la mediana de CDMX:

| insumo | menudeo ($/kg) | brecha menudeo | diagnóstico | aproximado |
| :---- | ----: | ----: | :---- | :---- |
| longaniza | 114.00 | +2.6 % | en rango | no |
| pastor | 108.00 | +41.7 % | caro | sí (pierna sin hueso) |
| suadero | 231.00 | −24.7 % | barato | sí (falda de res) |

**Lectura:** son datos sintéticos del proveedor contra precios reales de mercado: sirven para probar el cálculo, no para opinar de la taquería.
«Caro» o «barato» = más de 10 % arriba o abajo del menudeo ([ADR 0022](../docs/adr/0022-p2-mercado-unidades-y-diagnostico.md)). Fuera de esas tres semanas no hay comparación: sale «sin dato».

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
