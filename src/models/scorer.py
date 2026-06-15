"""Composite Scorer — 0-100 score across 5 dimensions.

Dimensions and weights:
  Rate Momentum   25%  — sector rate index trend (3M change)
  Valuation       25%  — P/NAV percentile vs history
  Supply Tightness 20% — orderbook/fleet + avg fleet age
  Balance Sheet   15%  — LTV + liquidity runway
  Capital Alloc.  15%  — dividend yield + governance proxy (charter coverage)
"""

from dataclasses import dataclass

from src.models.nav_engine import NAVResult
from src.models.fcf_engine import FCFResult
from src.config.universe import SECTOR_NAV_RANGES


SIGNAL_THRESHOLDS = {
    "BUY":   75,
    "HOLD":  50,
    "AVOID": 25,
}


@dataclass
class ScoreResult:
    ticker: str
    total_score: float
    rate_momentum_score: float    # /25
    valuation_score: float        # /25
    supply_tightness_score: float # /20
    balance_sheet_score: float    # /15
    capital_alloc_score: float    # /15
    signal: str                   # BUY / HOLD / AVOID / SELL
    p_nav: float
    fcf_yield_pct: float          # base 12m FCF / stock price * 100
    rate_momentum_pct: float


def _rate_momentum_score(momentum_3m_pct: float) -> float:
    """Score 0-25 based on rate direction and magnitude."""
    # Normalize: ±30% range maps to 0-25
    clamped = max(-30, min(30, momentum_3m_pct))
    return round((clamped + 30) / 60 * 25, 1)


def _valuation_score(p_nav: float, sector: str) -> float:
    """Score 0-25: cheaper vs historical range = higher score."""
    trough, mean, peak = SECTOR_NAV_RANGES.get(sector, (0.45, 0.90, 1.75))
    if p_nav <= trough:
        return 25.0
    if p_nav >= peak:
        return 0.0
    # Linear scale within trough-peak range
    return round((peak - p_nav) / (peak - trough) * 25, 1)


def _supply_tightness_score(
    orderbook_pct: float = 8.0,
    avg_fleet_age: float = 10.0,
) -> float:
    """Score 0-20.

    Low orderbook (tight future supply) → high score.
    Old fleet (scrapping candidates) → bonus.

    Orderbook/fleet ratio:
      <5%   → very tight → 16pts
      5-10% → tight      → 12pts
      10-15%→ moderate   → 8pts
      >15%  → loose      → 4pts

    Fleet age bonus:
      >15yr → +4pts
      10-15 → +3pts
      5-10  → +1pt
      <5yr  → 0pt
    """
    if orderbook_pct < 5:
        ob_score = 16.0
    elif orderbook_pct < 10:
        ob_score = 12.0
    elif orderbook_pct < 15:
        ob_score = 8.0
    else:
        ob_score = 4.0

    if avg_fleet_age > 15:
        age_bonus = 4.0
    elif avg_fleet_age > 10:
        age_bonus = 3.0
    elif avg_fleet_age > 5:
        age_bonus = 1.0
    else:
        age_bonus = 0.0

    return round(min(ob_score + age_bonus, 20.0), 1)


def _balance_sheet_score(
    net_debt_usd_m: float,
    fleet_mv_usd_m: float,
    annual_fcf_base_usd_m: float,
) -> float:
    """Score 0-15.

    Net LTV = net_debt / fleet_mv:
      <20%   → 10pts
      20-40% → 7pts
      40-60% → 4pts
      >60%   → 1pt

    Liquidity runway = fleet_mv / |annual_fcf| if FCF negative else always ok (+5pts max):
      FCF positive → 5pts
      FCF negative, runway > 3yr → 3pts
      FCF negative, runway 1-3yr → 1pt
      FCF negative, runway < 1yr → 0pt
    """
    ltv = net_debt_usd_m / max(fleet_mv_usd_m, 1)
    if ltv < 0.20:
        ltv_score = 10.0
    elif ltv < 0.40:
        ltv_score = 7.0
    elif ltv < 0.60:
        ltv_score = 4.0
    else:
        ltv_score = 1.0

    if annual_fcf_base_usd_m >= 0:
        liq_score = 5.0
    else:
        runway = fleet_mv_usd_m / max(abs(annual_fcf_base_usd_m), 1)
        if runway > 3:
            liq_score = 3.0
        elif runway > 1:
            liq_score = 1.0
        else:
            liq_score = 0.0

    return round(min(ltv_score + liq_score, 15.0), 1)


def _capital_alloc_score(
    charter_coverage_pct: float,
    fcf_yield_pct: float,
) -> float:
    """Score 0-15.

    FCF yield (proxy for dividend capacity):
      >20% → 8pts
      >10% → 6pts
      >5%  → 4pts
      >0%  → 2pts
      ≤0%  → 0pt

    Charter coverage (governance proxy: consistent long-term planning):
      >50% → 7pts (very visible cash flows)
      25-50%→ 5pts
      10-25%→ 3pts
      <10% → 1pt
    """
    if fcf_yield_pct > 20:
        yield_score = 8.0
    elif fcf_yield_pct > 10:
        yield_score = 6.0
    elif fcf_yield_pct > 5:
        yield_score = 4.0
    elif fcf_yield_pct > 0:
        yield_score = 2.0
    else:
        yield_score = 0.0

    if charter_coverage_pct > 50:
        charter_score = 7.0
    elif charter_coverage_pct > 25:
        charter_score = 5.0
    elif charter_coverage_pct > 10:
        charter_score = 3.0
    else:
        charter_score = 1.0

    return round(min(yield_score + charter_score, 15.0), 1)


def _signal(score: float) -> str:
    if score >= SIGNAL_THRESHOLDS["BUY"]:
        return "BUY"
    if score >= SIGNAL_THRESHOLDS["HOLD"]:
        return "HOLD"
    if score >= SIGNAL_THRESHOLDS["AVOID"]:
        return "AVOID"
    return "SELL"


def compute_score(
    nav: NAVResult,
    fcf: FCFResult,
    stock_price: float,
    sector: str,
    rate_momentum_pct: float = 0.0,
    orderbook_pct: float = 8.0,
) -> ScoreResult:
    """Compute composite 0-100 score for a shipping stock."""
    p_nav = nav.p_nav(stock_price)

    # FCF yield = base 12m FCF per share / stock price
    base_fcf = fcf.fcf_per_share_12m[1]
    fcf_yield = (base_fcf / stock_price * 100) if stock_price > 0 else 0.0

    # Weighted average fleet age
    avg_age = 10.0  # default; refined below if vessel group data available
    if nav.total_vessels > 0:
        avg_age = sum(
            g.avg_age_years * g.count
            for g in []  # vessel groups not passed through NAVResult; use default
        ) or 10.0

    rm_score  = _rate_momentum_score(rate_momentum_pct)
    val_score = _valuation_score(p_nav, sector)
    sup_score = _supply_tightness_score(orderbook_pct, avg_age)
    bs_score  = _balance_sheet_score(
        nav.net_debt_usd_m,
        nav.fleet_market_value_usd_m,
        fcf.annual_fcf_base_usd_m,
    )
    ca_score  = _capital_alloc_score(fcf.charter_coverage_pct, fcf_yield)

    total = round(rm_score + val_score + sup_score + bs_score + ca_score, 1)

    return ScoreResult(
        ticker=nav.ticker,
        total_score=total,
        rate_momentum_score=rm_score,
        valuation_score=val_score,
        supply_tightness_score=sup_score,
        balance_sheet_score=bs_score,
        capital_alloc_score=ca_score,
        signal=_signal(total),
        p_nav=round(p_nav, 2) if p_nav == p_nav else 0.0,
        fcf_yield_pct=round(fcf_yield, 1),
        rate_momentum_pct=round(rate_momentum_pct, 1),
    )
