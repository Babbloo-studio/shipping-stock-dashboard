"""Master pipeline — run all models and return scored results for all stocks."""

import pandas as pd
import structlog

from src.config.universe import UNIVERSE, TICKER_MAP, SECTOR_RATE_INDEX
from src.ingestion.fleet import load_all_fleets
from src.ingestion.prices import fetch_current_prices
from src.ingestion.rates import get_current_rates, get_rate_momentum
from src.models.nav_engine import compute_nav
from src.models.rate_forecast import forecast_rates
from src.models.fcf_engine import compute_fcf
from src.models.scorer import compute_score, ScoreResult
from src.models.nav_engine import NAVResult
from src.models.fcf_engine import FCFResult

log = structlog.get_logger()

# Sector orderbook-to-fleet ratios (updated manually monthly from Bimco)
ORDERBOOK_PCT = {
    "Crude Tanker":   7.2,
    "Product Tanker": 9.8,
    "Dry Bulk":       8.4,
    "LNG":            22.0,
    "Container":      24.0,
    "Diversified":    9.0,
}


def run_full_pipeline() -> pd.DataFrame:
    """Run all models and return one row per stock with all metrics.

    Returns DataFrame with columns:
      ticker, name, sector, price, change_pct, nav_per_share, p_nav,
      fcf_yield_pct, rate_momentum_pct, total_score, signal,
      fcf_bear, fcf_base, fcf_bull, breakeven_tce, annual_fcf_usd_m,
      fleet_mv_usd_m, net_debt_usd_m, total_vessels
    """
    log.info("pipeline_start")

    # 1. Load fleet data
    fleets = load_all_fleets()
    log.info("fleets_loaded", count=len(fleets))

    # 2. Fetch current prices
    prices_df = fetch_current_prices()
    price_map: dict[str, float] = {}
    chg_map: dict[str, float] = {}
    if not prices_df.empty:
        for _, row in prices_df.iterrows():
            t = row["ticker"]
            price_map[t] = float(row["price"]) if not pd.isna(row["price"]) else 0.0
            chg_map[t] = float(row["change_pct"]) if not pd.isna(row["change_pct"]) else 0.0

    # 3. Get current rate levels
    rates = get_current_rates()
    log.info("rates_loaded", keys=list(rates.keys()))

    rows = []
    for stock in UNIVERSE:
        ticker = stock.ticker
        fleet = fleets.get(ticker)
        if fleet is None:
            log.warning("no_fleet_data", ticker=ticker)
            continue

        price = price_map.get(ticker, 0.0)
        if price <= 0:
            log.warning("no_price", ticker=ticker)
            # still compute NAV/FCF but flag price as missing
            price = 1.0  # placeholder

        sector = stock.sector
        rate_index = SECTOR_RATE_INDEX.get(sector, "BDI")
        current_rate = rates.get(rate_index, rates.get("BDI", 1400))
        momentum = get_rate_momentum(rate_index, lookback_days=90)
        orderbook = ORDERBOOK_PCT.get(sector, 9.0)

        # 4. NAV
        nav: NAVResult = compute_nav(fleet)

        # 5. Rate forecast
        rate_scenario = forecast_rates(rate_index, current_rate, momentum)

        # 6. FCF scenarios
        fcf: FCFResult = compute_fcf(fleet, rate_scenario)

        # 7. Composite score
        score: ScoreResult = compute_score(
            nav, fcf, price, sector, momentum, orderbook
        )

        rows.append({
            "ticker": ticker,
            "name": stock.name,
            "sector": sector,
            "exchange": stock.exchange,
            "price": price_map.get(ticker, 0.0),
            "change_pct": chg_map.get(ticker, 0.0),
            "nav_per_share": round(nav.nav_per_share, 2),
            "p_nav": score.p_nav,
            "fcf_yield_pct": score.fcf_yield_pct,
            "rate_momentum_pct": score.rate_momentum_pct,
            "total_score": score.total_score,
            "signal": score.signal,
            "rate_momentum_score": score.rate_momentum_score,
            "valuation_score": score.valuation_score,
            "supply_tightness_score": score.supply_tightness_score,
            "balance_sheet_score": score.balance_sheet_score,
            "capital_alloc_score": score.capital_alloc_score,
            "fcf_bear_12m": round(fcf.fcf_per_share_12m[0], 2),
            "fcf_base_12m": round(fcf.fcf_per_share_12m[1], 2),
            "fcf_bull_12m": round(fcf.fcf_per_share_12m[2], 2),
            "fcf_bear_3m": round(fcf.fcf_per_share_3m[0], 2),
            "fcf_base_3m": round(fcf.fcf_per_share_3m[1], 2),
            "fcf_bull_3m": round(fcf.fcf_per_share_3m[2], 2),
            "breakeven_tce": fcf.breakeven_tce,
            "annual_fcf_base_usd_m": round(fcf.annual_fcf_base_usd_m, 1),
            "fleet_mv_usd_m": round(nav.fleet_market_value_usd_m, 1),
            "net_debt_usd_m": nav.net_debt_usd_m,
            "total_vessels": nav.total_vessels,
            "charter_coverage_pct": fleet.charter_coverage_pct,
            "rate_index": rate_index,
            "current_rate": current_rate,
            "rate_bear_12m": rate_scenario.bear_12m,
            "rate_base_12m": rate_scenario.base_12m,
            "rate_bull_12m": rate_scenario.bull_12m,
        })

    df = pd.DataFrame(rows)
    log.info("pipeline_complete", rows=len(df))
    return df
