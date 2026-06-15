"""Rate Monitor Page — live freight rate indices and forecasts."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.ingestion.rates import get_current_rates, fetch_bdi_history, fetch_macro_snapshot
from src.models.rate_forecast import forecast_rates, LONG_RUN_MEANS
from src.config.universe import SECTORS

st.set_page_config(page_title="Rate Monitor", page_icon="📈", layout="wide")

@st.cache_data(ttl=3600)
def load_rates():
    return get_current_rates()

@st.cache_data(ttl=86400)
def load_bdi_history():
    return fetch_bdi_history(days=730)

@st.cache_data(ttl=3600)
def load_macro():
    return fetch_macro_snapshot()

st.title("📈 Freight Rate Monitor")

rates = load_rates()
macro = load_macro()

# ── Current rate snapshot ─────────────────────────────────────────────────────
st.subheader("Current Rate Levels")
cols = st.columns(5)
rate_labels = {
    "BDI": "Baltic Dry Index",
    "BDTI": "Baltic Dirty Tanker",
    "BCTI": "Baltic Clean Tanker",
    "LNG_PROXY": "LNG Spot ($/day)",
    "SCFI_PROXY": "Container SCFI",
}
for i, (k, label) in enumerate(rate_labels.items()):
    val = rates.get(k, 0)
    mean = LONG_RUN_MEANS.get(k, val)
    delta_pct = (val - mean) / mean * 100 if mean > 0 else 0
    cols[i].metric(label, f"{val:,.0f}", f"{delta_pct:+.1f}% vs LT avg")

st.divider()

# ── BDI history chart ─────────────────────────────────────────────────────────
st.subheader("BDI History (2 years)")
bdi_hist = load_bdi_history()
if not bdi_hist.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=bdi_hist.index, y=bdi_hist.iloc[:, 0],
        name="BDI", line=dict(color="#3b82f6", width=2), fill="tozeroy",
        fillcolor="rgba(59,130,246,0.08)"
    ))
    fig.add_hline(
        y=LONG_RUN_MEANS["BDI"],
        line_dash="dash", line_color="#6b7280",
        annotation_text="Long-run avg",
    )
    fig.update_layout(
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="BDI Level",
        xaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(
        "Live BDI history requires a FRED API key. "
        "Set `FRED_API_KEY` in your `.env` file (free at fred.stlouisfed.org). "
        "Showing synthetic rate levels in the meantime."
    )

st.divider()

# ── Rate forecasts ─────────────────────────────────────────────────────────────
st.subheader("Rate Forecasts (Mean-Reversion Scenarios)")

index_options = ["BDI", "BDTI", "BCTI", "LNG_PROXY", "SCFI_PROXY"]
sel_index = st.selectbox("Rate index", index_options)
current = rates.get(sel_index, LONG_RUN_MEANS.get(sel_index, 1000))

scenario = forecast_rates(sel_index, current)

s1, s2, s3 = st.columns(3)
s1.metric("Bear 3M", f"{scenario.bear_3m:,.0f}", f"({(scenario.bear_3m-current)/current*100:+.0f}%)")
s2.metric("Base 3M", f"{scenario.base_3m:,.0f}", f"({(scenario.base_3m-current)/current*100:+.0f}%)")
s3.metric("Bull 3M", f"{scenario.bull_3m:,.0f}", f"({(scenario.bull_3m-current)/current*100:+.0f}%)")

s4, s5, s6 = st.columns(3)
s4.metric("Bear 12M", f"{scenario.bear_12m:,.0f}", f"({(scenario.bear_12m-current)/current*100:+.0f}%)")
s5.metric("Base 12M", f"{scenario.base_12m:,.0f}", f"({(scenario.base_12m-current)/current*100:+.0f}%)")
s6.metric("Bull 12M", f"{scenario.bull_12m:,.0f}", f"({(scenario.bull_12m-current)/current*100:+.0f}%)")

# Scenario fan chart
horizons = [0, 90, 180, 360]
bear_vals = [current, scenario.bear_3m, scenario.bear_6m, scenario.bear_12m]
base_vals = [current, scenario.base_3m, scenario.base_6m, scenario.base_12m]
bull_vals = [current, scenario.bull_3m, scenario.bull_6m, scenario.bull_12m]

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=horizons, y=bull_vals, name="Bull (75th pct)",
    line=dict(color="#22c55e", dash="dash"), mode="lines+markers"
))
fig2.add_trace(go.Scatter(
    x=horizons, y=base_vals, name="Base (50th pct)",
    line=dict(color="#3b82f6", width=2), mode="lines+markers"
))
fig2.add_trace(go.Scatter(
    x=horizons, y=bear_vals, name="Bear (25th pct)",
    line=dict(color="#ef4444", dash="dash"), mode="lines+markers",
    fill="tonexty", fillcolor="rgba(59,130,246,0.08)"
))
fig2.add_hline(
    y=LONG_RUN_MEANS.get(sel_index, current),
    line_dash="dot", line_color="#6b7280",
    annotation_text="Long-run mean"
)
fig2.update_layout(
    height=300, margin=dict(l=0, r=60, t=10, b=0),
    xaxis=dict(tickvals=[0, 90, 180, 360], ticktext=["Now", "3M", "6M", "12M"]),
    yaxis_title=sel_index,
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Macro features ─────────────────────────────────────────────────────────────
st.subheader("Macro Features")
if macro:
    mc = st.columns(len(macro))
    for i, (k, v) in enumerate(macro.items()):
        mc[i].metric(k.replace("_", " ").title(), f"{v:.2f}")
else:
    st.info("Macro data loading...")

st.divider()

# ── Orderbook snapshot ─────────────────────────────────────────────────────────
st.subheader("Orderbook-to-Fleet Ratios (Monthly Bimco Data)")
ob_data = {
    "Crude Tanker":   7.2,
    "Product Tanker": 9.8,
    "Dry Bulk":       8.4,
    "LNG":            22.0,
    "Container":      24.0,
    "Diversified":    9.0,
}
ob_df = pd.DataFrame(list(ob_data.items()), columns=["Sector", "Orderbook %"])
ob_df["Assessment"] = ob_df["Orderbook %"].apply(
    lambda x: "🟢 Tight" if x < 10 else ("🟡 Moderate" if x < 15 else "🔴 Heavy")
)
st.dataframe(ob_df, hide_index=True, use_container_width=True)
st.caption(
    "Orderbook/fleet < 10% historically correlates with rate upswings. "
    "Source: Bimco fleet analysis (manual monthly update)."
)
