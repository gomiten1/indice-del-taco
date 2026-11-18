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


def test_p2_sin_datos_dice_aun_sin_datos(monkeypatch):
    st = correr_dashboard(monkeypatch)
    mensajes = [str(c.args[0]) for c in st.info.call_args_list]
    assert any("Aún sin datos" in m and "PROFECO" in m for m in mensajes)


def test_p3_muestra_sin_dato_para_los_insumos_sin_precio(monkeypatch):
    st = correr_dashboard(monkeypatch)
    tablas = [c.args[0] for c in st.dataframe.call_args_list if isinstance(c.args[0], pd.DataFrame)]
    p3 = next(t for t in tablas if "insumo" in t.columns)
    assert "Sin dato" in set(p3["Aportación al cambio"]) and "100.0 %" in set(p3["Aportación al cambio"])
    assert not (p3["Aportación al cambio"] == "0.0 %").any()
