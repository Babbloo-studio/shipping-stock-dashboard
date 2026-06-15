"""Load and parse fleet data from local JSON files."""

import json
import os
from dataclasses import dataclass

import structlog

log = structlog.get_logger()

FLEET_DIR = os.path.join(os.path.dirname(__file__), "../../data/fleet")


@dataclass
class VesselGroup:
    vessel_type: str
    count: int
    avg_age_years: float
    avg_dwt: int
    eco_fitted: bool
    scrubber_fitted: bool


@dataclass
class FleetData:
    ticker: str
    total_vessels: int
    vessel_groups: list[VesselGroup]
    net_debt_usd_millions: float
    cash_usd_millions: float
    shares_outstanding_millions: float
    charter_coverage_pct: float       # % of fleet on time charter
    avg_tc_rate_per_day: float         # contracted TC rate if on charter
    opex_per_day: float                # avg opex per vessel
    interest_per_day: float            # total daily interest / fleet size


def load_fleet(ticker: str) -> FleetData | None:
    path = os.path.join(FLEET_DIR, f"{ticker}.json")
    if not os.path.exists(path):
        log.warning("fleet_data_missing", ticker=ticker)
        return None
    try:
        with open(path) as f:
            d = json.load(f)
        groups = [
            VesselGroup(
                vessel_type=g["type"],
                count=g["count"],
                avg_age_years=g["avg_age_years"],
                avg_dwt=g["avg_dwt"],
                eco_fitted=g["eco_fitted"],
                scrubber_fitted=g["scrubber_fitted"],
            )
            for g in d["vessel_groups"]
        ]
        return FleetData(
            ticker=d["ticker"],
            total_vessels=d["total_vessels"],
            vessel_groups=groups,
            net_debt_usd_millions=d["net_debt_usd_millions"],
            cash_usd_millions=d["cash_usd_millions"],
            shares_outstanding_millions=d["shares_outstanding_millions"],
            charter_coverage_pct=d["charter_coverage_pct"],
            avg_tc_rate_per_day=d["avg_tc_rate_per_day"],
            opex_per_day=d["opex_per_day"],
            interest_per_day=d["interest_per_day"],
        )
    except Exception as e:
        log.error("fleet_load_failed", ticker=ticker, error=str(e))
        return None


def load_all_fleets() -> dict[str, FleetData]:
    result = {}
    for fname in os.listdir(FLEET_DIR):
        if fname.endswith(".json"):
            ticker = fname.replace(".json", "")
            fd = load_fleet(ticker)
            if fd:
                result[ticker] = fd
    return result
