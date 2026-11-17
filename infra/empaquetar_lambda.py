"""Empaqueta codigo de src/ para Lambda en infra/build/<nombre>.zip (reproducible: mismo codigo, mismo zip).

Uso:  python infra/empaquetar_lambda.py banxico     # un solo modulo: src/ingesta/banxico.py
      python infra/empaquetar_lambda.py pipeline    # silver y gold: src/ingesta, src/transformacion y src/handlers
"""
import hashlib
import sys
import zipfile
from pathlib import Path

raiz = Path(__file__).resolve().parent.parent
nombre = sys.argv[1] if len(sys.argv) > 1 else "banxico"
src = raiz / "src"
if nombre == "pipeline":
    archivos = sorted(p for d in ("ingesta", "transformacion", "handlers") for p in (src / d).rglob("*.py"))
else:
    archivos = [src / "ingesta" / f"{nombre}.py"]
destino = raiz / "infra" / "build" / f"{nombre}.zip"
destino.parent.mkdir(exist_ok=True)

with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
    for p in archivos:
        # banxico va en la raiz del zip (Handler banxico.handler); el pipeline conserva sus paquetes
        arc = p.name if nombre != "pipeline" else p.relative_to(src).as_posix()
        info = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))  # fecha fija: zip reproducible
        info.external_attr = 0o644 << 16
        z.writestr(info, p.read_bytes())
huella = hashlib.sha256(destino.read_bytes()).hexdigest()[:8]
print(destino)
print(f"llave sugerida: lambdas/{nombre}-{huella}.zip  (cambia con el codigo, asi CloudFormation detecta la actualizacion)")
