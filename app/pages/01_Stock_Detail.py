"""Stock Detail Page — deep dive into a single shipping stock."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.models.pipeline import run_full_pipeline
from src.ingestion.prices import fetch_price_history
from src.ingestion.fleet import load_fleet
from src.config.universe import TICKER_MAP

st.set_page_config(page_title="Stock Detail", page_icon="📊", layout="wide")

@st.cache_data(ttl=1800)
def load_data():
    return run_full_pipeline()

@st.cache_data(ttl=3600)
def get_history(ticker):
    return fetch_price_history(ticker, period="2y")

df = load_data()

st.title("📊 Stock Deep-Dive")

ticker = st.selectbox("Select stock", df["ticker"].tolist())
row = df[df["ticker"] == ticker].iloc[0]
stock = TICKER_MAP.get(ticker)
fleet = load_fleet(ticker)

# ── Header ────────────────────────────────────────────────────────────────────
sig = row["signal"]
sig_color = {"BUY": "#22c55e", "HOLD": "#eab308", "AVOID": "#f97316", "SELL": "#ef4444"}.get(sig, "gray")
st.markdown(
    f"## {row['name']} &nbsp; `{ticker}` &nbsp; "
    f"<span style='color:{sig_color};font-size:1.2em;font-weight:700'>{sig}</span>",
    unsafe_allow_html=True
)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Price", f"${row['price']:.2f}", f"{row['change_pct']:+.1f}%")
c2.metric("Score", f"{row['total_score']}/100")
c3.metric("P/NAV", f"{row['p_nav']:.2f}x")
c4.metric("NAV/share", f"${row['nav_per_share']:.2f}")
c5.metric("FCF Yield", f"{row['fcf_yield_pct']:.1f}%")
c6.metric("Rate Mom. (3M)", f"{row['rate_momentum_pct']:+.1f}%")

st.divider()

# ── Price History with NAV overlay ────────────────────────────────────────────
st.subheader("Price History vs NAV")
hist = get_history(ticker)
if not hist.empty and "Close" in hist.columns:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist["date"], y=hist["Close"],
        name="Stock Price", line=dict(color="#3b82f6", width=2)
    ))
    fig.add_hline(
        y=row["nav_per_share"],
        line_dash="dash", line_color="#22c55e",
        annotation_text=f"NAV ${row['nav_per_share']:.2f}",
        annotation_position="right",
    )
    fig.update_layout(
        height=300, margin=dict(l=0, r=60, t=10, b=0),
        yaxis_title="Price (USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Price history unavailable.")

# ── NAV breakdown ─────────────────────────────────────────────────────────────
st.subheader("NAV Breakdown")
n1, n2, n3 = st.columns(3)
n1.metric("Fleet Market Value", f"${row['fleet_mv_usd_m']:.0f}M")
n2.metric("Net Debt", f"${row['net_debt_usd_m']:.0f}M")
n3.metric("NAV", f"${row['fleet_mv_usd_m'] - row['net_debt_usd_m']:.0f}M")

if fleet:
    st.markdown("**Fleet Composition**")
    fleet_rows = []
    for g in fleet.vessel_groups:
        from src.models.nav_engine import vessel_market_value
        mv = vessel_market_value(g.vessel_type, g.avg_age_years, g.eco_fitted, g.scrubber_fitted)
        fleet_rows.append({
            "Type": g.vessel_type,
            "Count": g.count,
            "Avg Age (yr)": f"{g.avg_age_years:.1f}",
            "MV/vessel ($M)": f"${mv:.1f}M",
            "Total MV ($M)": f"${mv * g.count:.0f}M",
            "Eco": "✓" if g.eco_fitted else "—",
            "Scrubber": "✓" if g.scrubber_fitted else "—",
        })
    st.dataframe(pd.DataFrame(fleet_rows), hide_index=True, use_container_width=True)

st.divider()

# ── FCF Scenarios ─────────────────────────────────────────────────────────────
st.subheader("FCF Scenarios (per share)")
scenarios = pd.DataFrame({
    "Horizon": ["3 Month", "3 Month", "3 Month", "12 Month", "12 Month", "12 Month"],
    "Scenario": ["Bear", "Base", "Bull", "Bear", "Base", "Bull"],
    "FCF/share": [
        row["fcf_bear_3m"], row["fcf_base_3m"], row["fcf_bull_3m"],
        row["fcf_bear_12m"], row["fcf_base_12m"], row["fcf_bull_12m"],
    ]
})
fig2 = px.bar(
    scenarios, x="Scenario", y="FCF/share", color="Scenario", facet_col="Horizon",
    color_discrete_map={"Bear": "#ef4444", "Base": "#eab308", "Bull": "#22c55e"},
    text="FCF/share",
)
fig2.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
fig2.add_hline(y=0, line_color="gray", line_dash="dot")
fig2.update_layout(height=320, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
st.plotly_chart(fig2, use_container_width=True)

f1, f2, f3 = st.columns(3)
f1.metric("Breakeven TCE", f"${row['breakeven_tce']:,.0f}/day")
f2.metric("Charter Coverage", f"{row['charter_coverage_pct']:.0f}%")
f3.metric("Annual FCF (base)", f"${row['annual_fcf_base_usd_m']:.1f}M")

st.divider()

# ── Rate Scenarios ─────────────────────────────────────────────────────────────
st.subheader(f"Rate Outlook — {row['rate_index']}")
r1, r2, r3, r4 = st.columns(4)
r1.metric("Current", f"{row['current_rate']:,.0f}")
r2.metric("Bear 12M", f"{row['rate_bear_12m']:,.0f}")
r3.metric("Base 12M", f"{row['rate_base_12m']:,.0f}")
r4.metric("Bull 12M", f"{row['rate_bull_12m']:,.0f}")

st.divider()

# ── Score breakdown ────────────────────────────────────────────────────────────
st.subheader("Score Breakdown")
score_df = pd.DataFrame([
    {"Dimension": "Rate Momentum (25)", "Score": row["rate_momentum_score"], "Max": 25},
    {"Dimension": "Valuation — P/NAV (25)", "Score": row["valuation_score"], "Max": 25},
    {"Dimension": "Supply Tightness (20)", "Score": row["supply_tightness_score"], "Max": 20},
    {"Dimension": "Balance Sheet (15)", "Score": row["balance_sheet_score"], "Max": 15},
    {"Dimension": "Capital Allocation (15)", "Score": row["capital_alloc_score"], "Max": 15},
])
score_df["Pct"] = score_df["Score"] / score_df["Max"]

fig3 = px.bar(
    score_df, x="Score", y="Dimension", orientation="h",
    color="Pct",
    color_continuous_scale=["#ef4444", "#eab308", "#22c55e"],
    range_color=[0, 1],
    text="Score",
)
fig3.update_traces(texttemplate="%{text:.0f}", textposition="outside")
fig3.update_layout(
    height=280, margin=dict(l=0, r=60, t=10, b=0),
    coloraxis_showscale=False,
    xaxis_range=[0, 28],
)
st.plotly_chart(fig3, use_container_width=True)
