"""Shipping Stock Dashboard — main entry point."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.models.pipeline import run_full_pipeline
from src.config.universe import SECTORS

st.set_page_config(
    page_title="Shipping Stock Dashboard",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .signal-buy   { color: #22c55e; font-weight: 700; font-size: 1.1em; }
  .signal-hold  { color: #eab308; font-weight: 700; font-size: 1.1em; }
  .signal-avoid { color: #f97316; font-weight: 700; font-size: 1.1em; }
  .signal-sell  { color: #ef4444; font-weight: 700; font-size: 1.1em; }
  .metric-label { font-size: 0.78em; color: #6b7280; }
  .score-bar    { height: 8px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Data loading with cache ──────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner="Fetching live data...")
def load_data() -> pd.DataFrame:
    return run_full_pipeline()


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🚢 Shipping Stocks")
    st.caption("Quantitative buy/sell signals for shipping equities")
    st.divider()

    sector_filter = st.multiselect(
        "Sub-sector",
        options=["All"] + SECTORS,
        default=["All"],
    )
    signal_filter = st.multiselect(
        "Signal",
        options=["All", "BUY", "HOLD", "AVOID", "SELL"],
        default=["All"],
    )
    min_score = st.slider("Min. composite score", 0, 100, 0)
    st.divider()
    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Prices refresh every 30 min · Fundamentals daily")


# ── Load data ────────────────────────────────────────────────────────────────
df = load_data()

if df.empty:
    st.error("Could not load data. Check your network connection.")
    st.stop()

# Apply filters
filtered = df.copy()
if "All" not in sector_filter and sector_filter:
    filtered = filtered[filtered["sector"].isin(sector_filter)]
if "All" not in signal_filter and signal_filter:
    filtered = filtered[filtered["signal"].isin(signal_filter)]
filtered = filtered[filtered["total_score"] >= min_score]


# ── Header metrics ───────────────────────────────────────────────────────────
st.title("🚢 Shipping Stock Dashboard")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Stocks tracked", len(df))
c2.metric("BUY signals", len(df[df["signal"] == "BUY"]))
c3.metric("HOLD signals", len(df[df["signal"] == "HOLD"]))
c4.metric("AVOID/SELL", len(df[df["signal"].isin(["AVOID", "SELL"])]))
c5.metric("Avg score", f"{df['total_score'].mean():.0f}/100")

st.divider()


# ── Score distribution chart ─────────────────────────────────────────────────
col_chart, col_table = st.columns([1, 2])

with col_chart:
    st.subheader("Score Distribution")
    fig = px.histogram(
        df, x="total_score", nbins=10,
        color_discrete_sequence=["#3b82f6"],
        labels={"total_score": "Composite Score"},
    )
    fig.add_vline(x=75, line_dash="dash", line_color="#22c55e", annotation_text="BUY")
    fig.add_vline(x=50, line_dash="dash", line_color="#eab308", annotation_text="HOLD")
    fig.add_vline(x=25, line_dash="dash", line_color="#ef4444", annotation_text="AVOID")
    fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.subheader("P/NAV vs Score (Bubble = Fleet Value)")
    fig2 = px.scatter(
        df, x="p_nav", y="total_score",
        size="fleet_mv_usd_m", color="sector",
        hover_name="ticker",
        hover_data={"signal": True, "fcf_yield_pct": ":.1f", "p_nav": ":.2f"},
        labels={"p_nav": "P/NAV Ratio", "total_score": "Composite Score"},
        size_max=40,
    )
    fig2.add_hline(y=75, line_dash="dash", line_color="#22c55e")
    fig2.add_vline(x=1.0, line_dash="dot", line_color="gray")
    fig2.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()


# ── Main screener table ───────────────────────────────────────────────────────
st.subheader(f"Screener — {len(filtered)} stocks")

SIGNAL_COLORS = {"BUY": "🟢", "HOLD": "🟡", "AVOID": "🟠", "SELL": "🔴"}

display = filtered[[
    "ticker", "name", "sector", "price", "change_pct",
    "p_nav", "fcf_yield_pct", "rate_momentum_pct", "total_score", "signal"
]].copy()

display["change_pct"] = display["change_pct"].map(lambda x: f"{x:+.1f}%")
display["p_nav"] = display["p_nav"].map(lambda x: f"{x:.2f}x")
display["fcf_yield_pct"] = display["fcf_yield_pct"].map(lambda x: f"{x:.1f}%")
display["rate_momentum_pct"] = display["rate_momentum_pct"].map(lambda x: f"{x:+.1f}%")
display["signal"] = display["signal"].map(lambda s: f"{SIGNAL_COLORS.get(s, '')} {s}")
display["price"] = display["price"].map(lambda x: f"${x:.2f}" if x > 0 else "N/A")
display = display.rename(columns={
    "ticker": "Ticker", "name": "Company", "sector": "Sector",
    "price": "Price", "change_pct": "Chg%", "p_nav": "P/NAV",
    "fcf_yield_pct": "FCF Yield", "rate_momentum_pct": "Rate Mom.",
    "total_score": "Score", "signal": "Signal"
})
display = display.sort_values("Score", ascending=False)

st.dataframe(display, use_container_width=True, hide_index=True, height=450)

st.divider()


# ── Score breakdown per stock ─────────────────────────────────────────────────
st.subheader("Score Breakdown")
selected_ticker = st.selectbox(
    "Select stock for score breakdown",
    options=df["ticker"].tolist(),
    index=0,
)
row = df[df["ticker"] == selected_ticker].iloc[0]

score_dims = {
    "Rate Momentum": (row["rate_momentum_score"], 25),
    "Valuation (P/NAV)": (row["valuation_score"], 25),
    "Supply Tightness": (row["supply_tightness_score"], 20),
    "Balance Sheet": (row["balance_sheet_score"], 15),
    "Capital Allocation": (row["capital_alloc_score"], 15),
}

b1, b2 = st.columns([1, 1])
with b1:
    st.markdown(f"**{row['name']} ({selected_ticker})**")
    sig = row["signal"]
    color = {"BUY": "#22c55e", "HOLD": "#eab308", "AVOID": "#f97316", "SELL": "#ef4444"}.get(sig, "gray")
    st.markdown(
        f"Score: **{row['total_score']}/100** &nbsp;|&nbsp; "
        f"<span style='color:{color};font-weight:700'>{SIGNAL_COLORS.get(sig,'')} {sig}</span>",
        unsafe_allow_html=True
    )
    st.markdown(f"P/NAV: **{row['p_nav']:.2f}x** &nbsp; NAV/share: **${row['nav_per_share']:.2f}** &nbsp; Price: **${row['price']:.2f}**")
    st.markdown(f"FCF/share (base 12m): **${row['fcf_base_12m']:.2f}** &nbsp; FCF Yield: **{row['fcf_yield_pct']:.1f}%**")
    st.markdown(f"Fleet: **{row['total_vessels']} vessels** &nbsp; Fleet MV: **${row['fleet_mv_usd_m']:.0f}M** &nbsp; Net Debt: **${row['net_debt_usd_m']:.0f}M**")

    for dim, (score, max_score) in score_dims.items():
        pct = score / max_score
        filled = int(pct * 20)
        bar = "█" * filled + "░" * (20 - filled)
        st.markdown(f"`{bar}` &nbsp; **{dim}**: {score:.0f}/{max_score}")

with b2:
    # FCF waterfall chart
    fcf_data = {
        "Bear 3M": row["fcf_bear_3m"],
        "Base 3M": row["fcf_base_3m"],
        "Bull 3M": row["fcf_bull_3m"],
        "Bear 12M": row["fcf_bear_12m"],
        "Base 12M": row["fcf_base_12m"],
        "Bull 12M": row["fcf_bull_12m"],
    }
    colors = ["#ef4444", "#eab308", "#22c55e", "#ef4444", "#eab308", "#22c55e"]
    fig3 = go.Figure(go.Bar(
        x=list(fcf_data.keys()),
        y=list(fcf_data.values()),
        marker_color=colors,
        text=[f"${v:.2f}" for v in fcf_data.values()],
        textposition="outside",
    ))
    fig3.add_hline(y=0, line_color="gray", line_dash="dot")
    fig3.update_layout(
        title=f"FCF/share Scenarios ({selected_ticker})",
        yaxis_title="FCF per share ($)",
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.caption(
    "Data: yfinance (prices) · FRED API (rates) · Company 20-F filings (fleet) · "
    "Model: NAV engine + mean-reversion rate forecast + FCF scenarios · "
    "Not financial advice."
)
