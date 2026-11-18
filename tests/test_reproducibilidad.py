"""N6: cualquier corrida se puede recalcular desde los datos originales y da exactamente lo mismo."""
import hashlib
import shutil
from datetime import date
from pathlib import Path

from datos_sinteticos.generador import escribir
from transformacion import pipeline_local

INPC = Path(__file__).parent.parent / "bronze_local/banxico/SP1/SP1_datos_2026-11-14.json"
FECHA = date(2026, 11, 16)


def huellas(raiz: Path, capas=("silver", "gold")) -> dict:
    return {p.relative_to(raiz).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for capa in capas for p in sorted((raiz / capa).rglob("*.parquet"))}


def correr(tmp_path, destino, ejecucion):
    return pipeline_local.correr(tmp_path / "sint/chat_proveedor.txt", tmp_path / "sint/receta.csv", INPC, FECHA, destino, ejecucion)


def test_borrar_silver_y_gold_y_recalcular_da_los_mismos_archivos(tmp_path):
    escribir(tmp_path / "sint", semilla=42)
    lago = tmp_path / "lago"
    correr(tmp_path, lago, "ejec-1")
    antes = huellas(lago)
    assert len(antes) > 40  # silver (semanas e INPC), receta y gold

    shutil.rmtree(lago / "silver"), shutil.rmtree(lago / "gold")  # lo derivado se tira; lo original (bronze) no se toca
    correr(tmp_path, lago, "ejec-2")
    assert huellas(lago) == antes  # silver y gold idénticos byte a byte, aunque cambie el id de la ejecución


def test_dos_corridas_independientes_coinciden(tmp_path):
    escribir(tmp_path / "sint", semilla=42)
    correr(tmp_path, tmp_path / "a", "x")
    correr(tmp_path, tmp_path / "b", "y")
    assert huellas(tmp_path / "a") == huellas(tmp_path / "b")


def test_el_id_de_ejecucion_solo_afecta_a_la_cuarentena(tmp_path):
    """Con errores en el chat, lo único que cambia entre corridas es el `ejecucion_id` guardado en cuarentena."""
    escribir(tmp_path / "sint", semilla=42, errores=True)
    correr(tmp_path, tmp_path / "a", "x")
    correr(tmp_path, tmp_path / "b", "y")
    assert huellas(tmp_path / "a") == huellas(tmp_path / "b")
    assert huellas(tmp_path / "a", ("cuarentena",)) != huellas(tmp_path / "b", ("cuarentena",))
