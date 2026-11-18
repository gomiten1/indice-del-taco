"""Pruebas del pipeline local y de la exportación del snapshot público (gold -> snapshot_gold/*.csv)."""
import hashlib
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from datos_sinteticos.generador import escribir
from transformacion import pipeline_local, snapshot
from transformacion.almacen import AlmacenLocal

from tests.datos import TRES_SERIES as INPC

MUESTRA_PROFECO = Path(__file__).parent.parent / "bronze_local/profeco/csv/b07_2026_q2_muestra.csv"


@pytest.fixture(scope="module")
def lago(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("lago")
    escribir(raiz / "sintetico", semilla=42)
    pipeline_local.correr(raiz / "sintetico/chat_proveedor.txt", raiz / "sintetico/receta.csv", INPC, date(2026, 11, 16), raiz / "lake", profeco=MUESTRA_PROFECO)
    return raiz / "lake"


def exportar(lago, salida):
    return snapshot.exportar(snapshot.leer_gold(AlmacenLocal(lago / "gold")), salida)


def test_pipeline_local_escribe_silver_cuarentena_y_gold(lago):
    assert (lago / "silver/silver_precio_proveedor").is_dir() and (lago / "silver/silver_inpc").is_dir()
    assert sorted(p.name for p in (lago / "gold").iterdir()) == [
        "comparativo_inflacion", "comparativo_proveedor", "contribucion_insumo", "costo_taco_semanal", "precio_insumo_semanal"]


def test_el_snapshot_trae_los_archivos_que_lee_el_dashboard(lago, tmp_path):
    exportar(lago, tmp_path)
    assert sorted(p.name for p in tmp_path.glob("*.csv")) == [
        "comparativo_inflacion.csv", "comparativo_proveedor.csv", "contribucion_insumo.csv", "costo_taco_semanal.csv", "precio_insumo_semanal.csv"]
    assert len(pd.read_csv(tmp_path / "costo_taco_semanal.csv")) == 117 and len(pd.read_csv(tmp_path / "comparativo_inflacion.csv")) == 18


def test_el_snapshot_coincide_con_lo_calculado_en_aws(lago, tmp_path):
    """Cifras que devolvió Athena sobre gold en AWS: pastor 6.90 -> 7.75 (indice 112.32), suadero 9.08 -> 10.18."""
    exportar(lago, tmp_path)
    c = pd.read_csv(tmp_path / "costo_taco_semanal.csv")
    base = c[~c.incluye_merma]
    p, s = base[base.tipo_taco == "pastor"], base[base.tipo_taco == "suadero"]
    assert (p.costo_taco_mxn.iloc[0], p.costo_taco_mxn.iloc[-1], p.indice_base100.iloc[-1]) == (6.90, 7.75, 112.32)
    assert (s.costo_taco_mxn.iloc[0], s.costo_taco_mxn.iloc[-1], s.indice_base100.iloc[-1]) == (9.08, 10.18, 112.12)


def test_sin_precios_del_proveedor_ni_columnas_privadas(lago, tmp_path):
    exportar(lago, tmp_path)
    for csv in tmp_path.glob("*.csv"):
        df = pd.read_csv(csv)
        assert "precio_proveedor_kg" not in df.columns
        if "fuente" in df.columns:
            assert "proveedor" not in set(df["fuente"])
    precios = pd.read_csv(tmp_path / "precio_insumo_semanal.csv")
    assert len(precios) > 0 and set(precios["fuente"]) == {"menudeo", "mayoreo"}  # solo mercado: lo del proveedor no sale


def test_p2_publica_la_brecha_pero_no_el_precio_del_proveedor(lago, tmp_path):
    exportar(lago, tmp_path)
    comp = pd.read_csv(tmp_path / "comparativo_proveedor.csv")
    assert list(comp.columns) == ["anio", "semana_iso", "insumo", "precio_menudeo_kg", "precio_mayoreo_kg", "brecha_menudeo_pct",
                                  "brecha_mayoreo_pct", "aproximado", "diagnostico"]
    assert set(comp["semana_iso"]) == {29, 30, 31} and set(comp["insumo"]) == {"longaniza", "pastor", "suadero"}


def test_p3_marca_sin_dato_en_vez_de_cero(lago, tmp_path):
    exportar(lago, tmp_path)
    c = pd.read_csv(tmp_path / "contribucion_insumo.csv")
    ultimo = c[c.trimestre == c.trimestre.max()]
    pastor = ultimo[ultimo.tipo_taco == "pastor"].sort_values("ranking")
    assert list(pastor.insumo) == ["pastor", "tortilla", "cebolla", "cilantro", "limon", "pina"]
    assert list(pastor.estado) == ["ok"] + ["sin dato"] * 5
    assert pastor.aportacion_pct.iloc[0] == 100.0 and pastor.aportacion_pct.iloc[1:].isna().all()


def test_la_exportacion_es_reproducible(lago, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    exportar(lago, a), exportar(lago, b)
    huella = lambda d: {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob("*.csv"))}
    assert huella(a) == huella(b)


def test_el_snapshot_trae_la_inflacion_de_alimentos_y_de_pecuarios(lago, tmp_path):
    exportar(lago, tmp_path)
    c = pd.read_csv(tmp_path / "comparativo_inflacion.csv")
    assert {"inpc_alimentos_base100", "inpc_pecuarios_base100"} <= set(c.columns)
    pastor = c[c.tipo_taco == "pastor"].set_index("mes")
    assert pastor.loc[1, ["inpc_general_base100", "inpc_alimentos_base100", "inpc_pecuarios_base100"]].tolist() == [100.0, 100.0, 100.0]
    assert pastor.inpc_alimentos_base100.notna().all() and pastor.inpc_pecuarios_base100.notna().all()
    assert pastor.loc[9, "inpc_alimentos_base100"] > pastor.loc[9, "inpc_general_base100"]  # los alimentos procesados subieron más que el INPC
