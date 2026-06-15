"""Tests for NAV engine."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models.nav_engine import vessel_market_value, compute_nav, _depreciation_factor
from src.ingestion.fleet import load_fleet


def test_depreciation_factor_bounds():
    assert _depreciation_factor(0) == 1.0
    assert _depreciation_factor(30) <= 0.1
    assert _depreciation_factor(10) < _depreciation_factor(5)


def test_vessel_market_value_vlcc():
    mv = vessel_market_value("VLCC", 5)
    assert 60 < mv < 120  # should be ~$78-100M for 5yr old VLCC


def test_vessel_market_value_eco_premium():
    mv_base = vessel_market_value("VLCC", 5, eco_fitted=False)
    mv_eco  = vessel_market_value("VLCC", 5, eco_fitted=True)
    assert mv_eco > mv_base


def test_vessel_market_value_old_ship():
    mv_new = vessel_market_value("Capesize", 3)
    mv_old = vessel_market_value("Capesize", 20)
    assert mv_old < mv_new * 0.5


def test_compute_nav_fro():
    fleet = load_fleet("FRO")
    assert fleet is not None
    nav = compute_nav(fleet)
    assert nav.fleet_market_value_usd_m > 0
    assert nav.nav_per_share > 0
    # FRO NAV/share should be in a reasonable range ($10-$40)
    assert 5 < nav.nav_per_share < 60


def test_p_nav_ratio():
    fleet = load_fleet("DHT")
    nav = compute_nav(fleet)
    # At a hypothetical $11 price
    p_nav = nav.p_nav(11.0)
    assert 0.1 < p_nav < 5.0
