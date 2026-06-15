"""NAV Engine — compute Net Asset Value per share for a shipping company.

Vessel market value estimated from age/type depreciation curves calibrated
to secondhand market data (literature: 2025 PMC XGBoost vessel valuation paper).
"""

from dataclasses import dataclass

from src.ingestion.fleet import FleetData, VesselGroup

# Newbuild price reference (USD millions) per vessel type — approximate 2024 market
NEWBUILD_PRICE = {
    "VLCC":           125.0,
    "Suezmax":         85.0,
    "Aframax":         70.0,
    "LR2":             65.0,
    "LR1":             55.0,
    "MR":              45.0,
    "Handy":           38.0,
    "Capesize":        62.0,
    "Panamax":         35.0,
    "Supramax":        30.0,
    "Handysize":       25.0,
    "LNGC":           240.0,
    "FSRU":           320.0,
    "Container_Large": 180.0,
    "Container_Mid":   80.0,
    "Container_Small": 35.0,
    "Bulker":          32.0,
    "Container":       60.0,
    "Panamax_Bulk":    35.0,
    "MR_Tanker":       45.0,
    "LPG":             42.0,
    "Offshore":        25.0,
}

# Depreciation curve: fraction of newbuild value retained at each age (years)
# Calibrated to Clarksons secondhand transaction data (simplified piecewise linear)
DEPRECIATION_CURVE = [
    (0,  1.00),
    (3,  0.88),
    (5,  0.78),
    (8,  0.65),
    (10, 0.56),
    (12, 0.47),
    (15, 0.37),
    (18, 0.28),
    (20, 0.20),
    (25, 0.10),
    (30, 0.04),
]

# Eco-fitted / scrubber premiums
ECO_PREMIUM = 0.06     # +6% to market value
SCRUBBER_PREMIUM = 0.04  # +4% to market value


def _depreciation_factor(age: float) -> float:
    """Interpolate depreciation factor for given vessel age."""
    curve = DEPRECIATION_CURVE
    if age <= curve[0][0]:
        return curve[0][1]
    if age >= curve[-1][0]:
        return curve[-1][1]
    for i in range(len(curve) - 1):
        a0, f0 = curve[i]
        a1, f1 = curve[i + 1]
        if a0 <= age <= a1:
            t = (age - a0) / (a1 - a0)
            return f0 + t * (f1 - f0)
    return 0.05


def vessel_market_value(
    vessel_type: str,
    age_years: float,
    eco_fitted: bool = False,
    scrubber_fitted: bool = False,
) -> float:
    """Return estimated secondhand market value in USD millions."""
    newbuild = NEWBUILD_PRICE.get(vessel_type, 50.0)
    factor = _depreciation_factor(age_years)
    mv = newbuild * factor
    if eco_fitted:
        mv *= (1 + ECO_PREMIUM)
    if scrubber_fitted:
        mv *= (1 + SCRUBBER_PREMIUM)
    return mv


@dataclass
class NAVResult:
    ticker: str
    fleet_market_value_usd_m: float
    net_debt_usd_m: float
    cash_usd_m: float
    nav_usd_m: float
    nav_per_share: float
    shares_outstanding_m: float
    total_vessels: int

    def p_nav(self, stock_price: float) -> float:
        """Return price-to-NAV ratio."""
        if self.nav_per_share <= 0:
            return float("nan")
        return stock_price / self.nav_per_share

    def nav_discount_pct(self, stock_price: float) -> float:
        """Positive = trading below NAV (cheap), negative = premium."""
        if self.nav_per_share <= 0:
            return 0.0
        return (self.nav_per_share - stock_price) / self.nav_per_share * 100


def compute_nav(fleet: FleetData) -> NAVResult:
    """Compute NAV for a company given its fleet data."""
    fleet_mv = 0.0
    for group in fleet.vessel_groups:
        mv_per_vessel = vessel_market_value(
            group.vessel_type,
            group.avg_age_years,
            group.eco_fitted,
            group.scrubber_fitted,
        )
        fleet_mv += mv_per_vessel * group.count

    gross_assets = fleet_mv + fleet.cash_usd_millions
    nav_usd_m = gross_assets - fleet.net_debt_usd_millions
    nav_per_share = (nav_usd_m * 1_000_000) / (fleet.shares_outstanding_millions * 1_000_000)

    return NAVResult(
        ticker=fleet.ticker,
        fleet_market_value_usd_m=fleet_mv,
        net_debt_usd_m=fleet.net_debt_usd_millions,
        cash_usd_m=fleet.cash_usd_millions,
        nav_usd_m=nav_usd_m,
        nav_per_share=nav_per_share,
        shares_outstanding_m=fleet.shares_outstanding_millions,
        total_vessels=fleet.total_vessels,
    )
