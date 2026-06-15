"""FCF Scenario Engine — compute Free Cash Flow per share under rate scenarios.

Methodology:
  Daily FCF/vessel = TCE_rate - Opex - G&A_allocated - Interest_allocated
  Annual FCF = Daily FCF * fleet * 365 * (1 - drydock_pct)
  FCF/share   = Annual FCF / shares_outstanding
"""

from dataclasses import dataclass

from src.ingestion.fleet import FleetData
from src.models.rate_forecast import RateScenario, get_sector_tce
from src.config.universe import TICKER_MAP, SECTOR_RATE_INDEX

DRYDOCK_PCT = 0.04          # ~15 days/year per vessel off-hire
VOYAGE_COST_FACTOR = 0.15   # voyage costs as % of gross TCE (fuel, port, etc.)
GNA_PER_DAY = 800           # $/vessel/day G&A overhead


@dataclass
class FCFResult:
    ticker: str
    # per scenario: (bear, base, bull)
    fcf_per_share_3m: tuple[float, float, float]
    fcf_per_share_6m: tuple[float, float, float]
    fcf_per_share_12m: tuple[float, float, float]
    breakeven_tce: float     # TCE rate at which FCF = 0
    daily_margin_base: float # base-case daily net margin per vessel
    charter_coverage_pct: float
    annual_fcf_base_usd_m: float


def _daily_fcf(tce_gross: float, opex: float, gna: float, interest: float) -> float:
    """Net daily cash flow per vessel."""
    net_tce = tce_gross * (1 - VOYAGE_COST_FACTOR)
    return net_tce - opex - gna - interest


def _annual_fcf(daily_per_vessel: float, n_vessels: int) -> float:
    """Annual FCF in USD millions."""
    return daily_per_vessel * n_vessels * 365 * (1 - DRYDOCK_PCT) / 1_000_000


def compute_fcf(
    fleet: FleetData,
    rate_scenario: RateScenario,
    vessel_type_hint: str = "",
) -> FCFResult:
    """Compute FCF per share across bear/base/bull scenarios."""
    opex = fleet.opex_per_day
    gna = GNA_PER_DAY
    interest = fleet.interest_per_day
    n = fleet.total_vessels
    shares = fleet.shares_outstanding_millions

    tc_pct = fleet.charter_coverage_pct / 100
    spot_pct = 1 - tc_pct
    tc_tce = fleet.avg_tc_rate_per_day

    def _scenario_fcf_per_share(rate_index_level: float) -> float:
        spot_tce = get_sector_tce(rate_scenario.index_name, rate_index_level, vessel_type_hint)
        blended_tce = spot_pct * spot_tce + tc_pct * tc_tce
        daily = _daily_fcf(blended_tce, opex, gna, interest)
        annual_usd_m = _annual_fcf(daily, n)
        return annual_usd_m * 1_000_000 / (shares * 1_000_000)

    # Breakeven: spot TCE at which daily FCF = 0
    # 0 = (1-vc) * tce - opex - gna - interest  =>  tce = (opex+gna+interest)/(1-vc)
    breakeven_gross = (opex + gna + interest) / (1 - VOYAGE_COST_FACTOR)

    # Base daily margin using base 12m forecast
    base_tce = get_sector_tce(rate_scenario.index_name, rate_scenario.base_12m, vessel_type_hint)
    blended_base = spot_pct * base_tce + tc_pct * tc_tce
    base_daily = _daily_fcf(blended_base, opex, gna, interest)
    annual_base = _annual_fcf(base_daily, n)

    return FCFResult(
        ticker=fleet.ticker,
        fcf_per_share_3m=(
            _scenario_fcf_per_share(rate_scenario.bear_3m),
            _scenario_fcf_per_share(rate_scenario.base_3m),
            _scenario_fcf_per_share(rate_scenario.bull_3m),
        ),
        fcf_per_share_6m=(
            _scenario_fcf_per_share(rate_scenario.bear_6m),
            _scenario_fcf_per_share(rate_scenario.base_6m),
            _scenario_fcf_per_share(rate_scenario.bull_6m),
        ),
        fcf_per_share_12m=(
            _scenario_fcf_per_share(rate_scenario.bear_12m),
            _scenario_fcf_per_share(rate_scenario.base_12m),
            _scenario_fcf_per_share(rate_scenario.bull_12m),
        ),
        breakeven_tce=round(breakeven_gross),
        daily_margin_base=round(base_daily),
        charter_coverage_pct=fleet.charter_coverage_pct,
        annual_fcf_base_usd_m=annual_base,
    )
