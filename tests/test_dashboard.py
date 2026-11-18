"""El dashboard se ejecuta contra el snapshot del repo y avisa cuando no hay datos (Streamlit simulado)."""
import os
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

RAIZ = Path(__file__).parent.parent


def correr_dashboard(monkeypatch):
    st = MagicMock()
    st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
    monkeypatch.setitem(__import__("sys").modules, "streamlit", st)
    monkeypatch.chdir(RAIZ)  # el dashboard lee snapshot_gold/ con ruta relativa a la raiz del repo
    exec(compile((RAIZ / "dashboard/app.py").read_text(encoding="utf-8"), "app.py", "exec"), {"__name__": "__main__"})
    return st


def test_el_dashboard_se_ejecuta_sin_errores(monkeypatch):
    st = correr_dashboard(monkeypatch)
    assert st.line_chart.call_count == 2


def test_p2_muestra_la_comparacion_y_hasta_que_semana_hay_mercado(monkeypatch):
    st = correr_dashboard(monkeypatch)
    avisos = [str(c.args[0]) for c in st.caption.call_args_list]
    assert any("2026-S29 a 2026-S31" in a and "ADR 0020" in a for a in avisos)
    tablas = [c.args[0] for c in st.dataframe.call_args_list if isinstance(c.args[0], pd.DataFrame)]
    p2 = next(t for t in tablas if "diagnostico" in t.columns)
    assert set(p2["insumo"]) == {"longaniza", "pastor", "suadero"} and "precio_proveedor_kg" not in p2.columns


def test_p2_sin_datos_dice_aun_sin_datos(monkeypatch, tmp_path):
    for nombre in ("costo_taco_semanal", "comparativo_inflacion", "contribucion_insumo", "precio_insumo_semanal"):
        (tmp_path / "snapshot_gold").mkdir(exist_ok=True)
        (tmp_path / "snapshot_gold" / f"{nombre}.csv").write_bytes((RAIZ / "snapshot_gold" / f"{nombre}.csv").read_bytes())
    (tmp_path / "snapshot_gold/comparativo_proveedor.csv").write_text("anio,semana_iso,insumo,precio_menudeo_kg,precio_mayoreo_kg,brecha_menudeo_pct,brecha_mayoreo_pct,aproximado,diagnostico\n")
    st = MagicMock()
    st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
    monkeypatch.setitem(__import__("sys").modules, "streamlit", st)
    monkeypatch.chdir(tmp_path)
    exec(compile((RAIZ / "dashboard/app.py").read_text(encoding="utf-8"), "app.py", "exec"), {"__name__": "__main__"})
    assert any("Aún sin datos" in str(c.args[0]) and "PROFECO" in str(c.args[0]) for c in st.info.call_args_list)


def test_p3_muestra_sin_dato_para_los_insumos_sin_precio(monkeypatch):
    st = correr_dashboard(monkeypatch)
    tablas = [c.args[0] for c in st.dataframe.call_args_list if isinstance(c.args[0], pd.DataFrame)]
    p3 = next(t for t in tablas if "Aportación al cambio" in t.columns)
    assert "Sin dato" in set(p3["Aportación al cambio"]) and "100.0 %" in set(p3["Aportación al cambio"])
    assert not (p3["Aportación al cambio"] == "0.0 %").any()
