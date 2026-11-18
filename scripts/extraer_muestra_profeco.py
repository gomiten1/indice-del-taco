"""Recorta un CSV de PROFECO a las filas que usa el pipeline (CDMX y los insumos del taco) para tener un archivo de prueba pequeño.

Uso: PYTHONPATH=src python scripts/extraer_muestra_profeco.py data/b07_2026_q2.csv bronze_local/profeco/csv/b07_2026_q2_muestra.csv
El silver de la muestra es idéntico al del archivo completo (mismas filas útiles), así que sirve para pruebas, CI y el snapshot.
"""
import sys

import pyarrow as pa
import pyarrow.csv as pcsv
import pyarrow.compute as pc

from transformacion.silver_mercado import ESTADO, PRODUCTOS, clasificar

origen, destino = sys.argv[1:3]
tabla = pcsv.read_csv(origen, convert_options=pcsv.ConvertOptions(column_types={"precio": pa.string()}, strings_can_be_null=False))
tabla = tabla.filter(pc.and_(pc.equal(tabla["estado"], ESTADO), pc.is_in(tabla["producto"], value_set=pa.array(PRODUCTOS))))
util = [clasificar(p, q) is not None for p, q in zip(tabla["producto"].to_pylist(), tabla["presentacion"].to_pylist())]
tabla = tabla.filter(pa.array(util))
pcsv.write_csv(tabla, destino)
print(f"{tabla.num_rows} filas -> {destino}")
