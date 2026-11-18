"""Series reales del INPC (Banxico) guardadas en bronze_local/, para las pruebas."""
from pathlib import Path

RAIZ = Path(__file__).parent.parent / "bronze_local/banxico"
ARCHIVOS = {
    "SP1": RAIZ / "SP1/SP1_datos_2026-11-14.json",
    "SP66540": RAIZ / "SP66540/SP66540_datos_2026-11-18.json",  # Alimentos, Bebidas y Tabaco (subyacente)
    "SP56386": RAIZ / "SP56386/SP56386_datos_2026-11-18.json",  # Pecuarios (no subyacente)
}


def inpc_json(serie: str) -> bytes:
    return ARCHIVOS[serie].read_bytes()


TRES_SERIES = [ARCHIVOS["SP1"], ARCHIVOS["SP66540"], ARCHIVOS["SP56386"]]
