"""Tests for composite scorer."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.ingestion.fleet import load_fleet
from src.models.nav_engine import compute_nav
from src.models.rate_forecast import forecast_rates
from src.models.fcf_engine import compute_fcf
from src.models.scorer import compute_score, _signal


def _score_for(ticker, price, rate_index, rate_level, sector, momentum=0.0):
    fleet = load_fleet(ticker)
    nav   = compute_nav(fleet)
    scen  = forecast_rates(rate_index, rate_level, momentum)
    fcf   = compute_fcf(fleet, scen)
    return compute_score(nav, fcf, price, sector, momentum)


def test_score_range():
    score = _score_for("SBLK", 27.0, "BDI", 1400, "Dry Bulk")
    assert 0 <= score.total_score <= 100


def test_cheap_stock_scores_higher():
    """Stock at 0.6x NAV should score higher valuation than at 1.5x NAV."""
    fleet = load_fleet("DHT")
    nav   = compute_nav(fleet)
    scen  = forecast_rates("BDTI", 682)
    fcf   = compute_fcf(fleet, scen)
    nav_ps = nav.nav_per_share
    score_cheap = compute_score(nav, fcf, nav_ps * 0.6, "Crude Tanker")
    score_dear  = compute_score(nav, fcf, nav_ps * 1.5, "Crude Tanker")
    assert score_cheap.valuation_score > score_dear.valuation_score


def test_signal_buy_threshold():
    assert _signal(80) == "BUY"
    assert _signal(60) == "HOLD"
    assert _signal(35) == "AVOID"
    assert _signal(15) == "SELL"


def test_all_stocks_scoreable():
    """Pipeline should produce a score for every stock with fleet data."""
    from src.ingestion.fleet import load_all_fleets
    fleets = load_all_fleets()
    for ticker, fleet in fleets.items():
        nav  = compute_nav(fleet)
        scen = forecast_rates("BDI", 1400)
        fcf  = compute_fcf(fleet, scen)
        score = compute_score(nav, fcf, 15.0, "Dry Bulk")
        assert 0 <= score.total_score <= 100, f"{ticker} score out of range"
