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

ultima_sem = costo["semana_iso"].max()
ultimo_costo = costo[costo["semana_iso"] == ultima_sem]

suadero_actual = ultimo_costo[(ultimo_costo["tipo_taco"] == "suadero") & (~ultimo_costo["incluye_merma"])].iloc[0]
pastor_base = ultimo_costo[(ultimo_costo["tipo_taco"] == "pastor") & (~ultimo_costo["incluye_merma"])].iloc[0]
pastor_merma_df = ultimo_costo[(ultimo_costo["tipo_taco"] == "pastor") & (ultimo_costo["incluye_merma"])]
pastor_merma_val = pastor_merma_df.iloc[0]["costo_taco_mxn"] if not pastor_merma_df.empty else pastor_base["costo_taco_mxn"] * 1.12

# P1: ¿Cuánto cuesta hoy cada taco?
st.subheader(f"1. ¿Cuánto cuesta hoy producir cada taco? (P1 — Semana {ultima_sem})")
col1, col2, col3 = st.columns(3)
col1.metric(
    "Taco de Suadero (receta estándar 55 g)",
    f"${suadero_actual['costo_taco_mxn']:.2f} MXN",
    f"Índice: {suadero_actual['indice_base100']} (Base 100)",
)
col2.metric(
    "Taco al Pastor (receta estándar 50 g)",
    f"${pastor_base['costo_taco_mxn']:.2f} MXN",
    f"Índice: {pastor_base['indice_base100']} (Base 100)",
)
col3.metric(
    "Taco al Pastor (con 12% merma trompo)",
    f"${pastor_merma_val:.2f} MXN",
    "Sensibilidad operativa (ADR 0008)",
)

costo_base = costo[~costo["incluye_merma"]]
st.line_chart(costo_base.pivot(index="semana_inicio", columns="tipo_taco", values="costo_taco_mxn"))

# P2: ¿Mi proveedor cobra caro o barato frente al mercado?
st.subheader("2. ¿El proveedor cobra caro o barato frente al mercado CDMX? (P2 — Aproximado)")
if comp.empty:
    st.info("Aún sin datos: la comparación contra el mercado necesita los precios de PROFECO, que todavía no se cargan al pipeline.")
else:
    ultima_comp = comp[comp["semana"] == ultima_sem][["insumo", "brecha_vs_mercado_pct", "diagnostico"]]
    if ultima_comp.empty:
        ultima_comp = comp[comp["semana"] == comp["semana"].max()][["insumo", "brecha_vs_mercado_pct", "diagnostico"]]
    st.dataframe(ultima_comp, use_container_width=True, hide_index=True)

# P3: ¿Qué insumo explica el aumento de costos?
st.subheader("3. ¿Qué insumo explica el aumento en el último trimestre? (P3)")
if contrib.empty:
    st.info("Aún sin datos: se necesitan al menos dos semanas de precios dentro de un trimestre.")
else:
    trimestre = contrib["trimestre"].max()
    top3 = contrib[(contrib["trimestre"] == trimestre) & (contrib["ranking"] <= 3)].copy()
    etiquetas = {"sin dato": "Sin dato", "sin cambio": "Sin cambio"}
    top3["Aportación al cambio"] = [etiquetas.get(e, f"{p:.1f} %") for e, p in zip(top3["estado"], top3["aportacion_pct"])]
    st.caption(f"Trimestre {trimestre}. «Sin dato» significa que todavía no hay precios de ese insumo (faltan los datos de mercado), no que aporte 0 %.")
    st.dataframe(top3[["tipo_taco", "ranking", "insumo", "Aportación al cambio"]], use_container_width=True, hide_index=True)

# P4: ¿Mi costo sube más o menos que la inflación?
st.subheader("4. Índice del Taco vs. Inflación Oficial INPC Banxico (Base 100) (P4)")
infl["periodo"] = infl["anio"].astype(str) + "-" + infl["mes"].astype(str).str.zfill(2)
piv_taco = infl.pivot(index="periodo", columns="tipo_taco", values="indice_taco_base100")
inpc_serie = infl.groupby("periodo")["inpc_general_base100"].first()
df_p4 = piv_taco.join(inpc_serie)
st.line_chart(df_p4)
