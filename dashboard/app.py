import pandas as pd
import streamlit as st

st.set_page_config(page_title="El Índice del Taco — La TaquerIA Opus", layout="wide")

st.title("El Índice del Taco — La TaquerIA Opus")
st.caption("Monitoreo semanal de costos de insumos (CDMX) · Datos agregados públicos (sin precios confidenciales de proveedor)")

with st.expander("Supuestos metodológicos y alcance del tablero (ADRs 0003–0009)", expanded=False):
    st.markdown(
        """
        - **Receta estándar por taco (ADR 0005 / 0007):** 55 g de suadero o 50 g de pastor por pieza (salsa fuera del costo base).
        - **Merma operativa (ADR 0008):** 12 % aplicada únicamente al trompo de pastor como escenario de sensibilidad.
        - **Privacidad (SOW §8):** Este tablero lee exclusivamente `snapshot_gold/` y no expone precios exactos del proveedor.
        - **Comparativo de mercado y contribución (P2 / P3):** Valores marcados como *aproximados* con referencia mediana CDMX (PROFECO).
        """
    )

costo = pd.read_csv("snapshot_gold/costo_taco_semanal.csv")
comp = pd.read_csv("snapshot_gold/comparativo_proveedor.csv")
infl = pd.read_csv("snapshot_gold/comparativo_inflacion.csv")
contrib = pd.read_csv("snapshot_gold/contribucion_insumo.csv")

ultima_sem = costo["semana"].max()
ultimo_costo = costo[costo["semana"] == ultima_sem].set_index("tipo_taco")

# P1: ¿Cuánto cuesta hoy cada taco?
st.subheader("1. ¿Cuánto cuesta hoy producir cada taco? (P1)")
col1, col2, col3 = st.columns(3)
col1.metric(
    "Taco de Suadero (receta estándar 55 g)",
    f"${ultimo_costo.loc['suadero', 'costo_taco_mxn']:.2f} MXN",
    f"Índice: {ultimo_costo.loc['suadero', 'indice_taco']} (Base 100)",
)
col2.metric(
    "Taco al Pastor (receta estándar 50 g)",
    f"${ultimo_costo.loc['pastor', 'costo_taco_mxn']:.2f} MXN",
    f"Índice: {ultimo_costo.loc['pastor', 'indice_taco']} (Base 100)",
)
col3.metric(
    "Taco al Pastor (con 12% merma trompo)",
    f"${ultimo_costo.loc['pastor', 'costo_taco_con_merma_mxn']:.2f} MXN",
    "Sensibilidad operativa (ADR 0008)",
)

st.line_chart(costo.pivot(index="semana", columns="tipo_taco", values="costo_taco_mxn"))

# P2: ¿Mi proveedor cobra caro o barato frente al mercado?
st.subheader("2. ¿El proveedor cobra caro o barato frente al mercado CDMX? (P2 — Aproximado)")
ultima_comp = comp[comp["semana"] == ultima_sem][["insumo", "brecha_vs_mercado_pct", "diagnostico"]]
st.dataframe(ultima_comp, use_container_width=True, hide_index=True)

# P3: ¿Qué insumo explica el aumento de costos?
st.subheader("3. ¿Qué insumo explica el aumento en el último trimestre? (P3 — Aproximado)")
top3 = contrib[contrib["ranking"] <= 3][["tipo_taco", "ranking", "insumo", "aporte_cambio_pct"]]
st.dataframe(top3, use_container_width=True, hide_index=True)

# P4: ¿Mi costo sube más o menos que la inflación?
st.subheader("4. Índice del Taco vs. Inflación Oficial INPC Banxico (Base 100) (P4)")
st.line_chart(infl.set_index("mes")[["indice_taco_suadero", "indice_taco_pastor", "inpc_general_base_100"]])