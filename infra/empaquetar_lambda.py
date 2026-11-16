"""Empaqueta un modulo de src/ingesta/ en infra/build/<modulo>.zip (reproducible: mismo codigo, mismo zip).

Uso:  python infra/empaquetar_lambda.py banxico
"""
import sys
import zipfile
from pathlib import Path

raiz = Path(__file__).resolve().parent.parent
modulo = sys.argv[1] if len(sys.argv) > 1 else "banxico"
origen = raiz / "src" / "ingesta" / f"{modulo}.py"
destino = raiz / "infra" / "build" / f"{modulo}.zip"
destino.parent.mkdir(exist_ok=True)

info = zipfile.ZipInfo(origen.name, date_time=(2026, 1, 1, 0, 0, 0))  # fecha fija: zip reproducible
info.external_attr = 0o644 << 16
with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(info, origen.read_bytes())
import hashlib
huella = hashlib.sha256(destino.read_bytes()).hexdigest()[:8]
print(destino)
print(f"llave sugerida: lambdas/{modulo}-{huella}.zip  (cambia con el codigo, asi CloudFormation detecta la actualizacion)")
