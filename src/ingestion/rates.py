"""Fetch freight rate indices and macro features.

Primary: FRED API (BDI = BDIY, BDTI).
Fallback: Yahoo Finance proxies for commodities when FRED key absent.
"""

import datetime
import requests
import pandas as pd
import yfinance as yf
import structlog

from src.config.settings import settings

log = structlog.get_logger()

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Yahoo Finance tickers used as macro proxies
MACRO_TICKERS = {
    "oil_brent": "BZ=F",
    "iron_ore_proxy": "VALE",   # Vale SA as iron ore proxy
    "coal_proxy": "BTU",         # Peabody Energy as coal proxy
    "usd_index": "DX-Y.NYB",
    "vix": "^VIX",
    "sp500": "^GSPC",
}

# Synthetic BDI approximate levels (fallback when no FRED key)
# Updated manually; should be replaced by live data
SYNTHETIC_RATES = {
    "BDI": 1420,
    "BDTI": 682,
    "BCTI": 720,
    "LNG_PROXY": 55000,   # $/day rough spot rate
    "SCFI_PROXY": 1800,   # SCFI index level
}


def _fred_fetch(series_id: str, days: int = 365) -> pd.DataFrame:
    """Fetch a FRED series as a date-indexed DataFrame."""
    if not settings.fred_api_key:
        return pd.DataFrame()
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    params = {
        "series_id": series_id,
        "api_key": settings.fred_api_key,
        "file_type": "json",
        "observation_start": start.isoformat(),
        "observation_end": end.isoformat(),
    }
    try:
        r = requests.get(FRED_BASE, params=params, timeout=10)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        df = pd.DataFrame(obs)[["date", "value"]]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna().set_index("date").rename(columns={"value": series_id})
        return df
    except Exception as e:
        log.warning("fred_fetch_failed", series=series_id, error=str(e))
        return pd.DataFrame()


def fetch_bdi_history(days: int = 365) -> pd.DataFrame:
    """Return BDI history. Uses FRED if key available, else returns empty."""
    return _fred_fetch("BDIY", days)


def fetch_bdti_history(days: int = 365) -> pd.DataFrame:
    return _fred_fetch("BDTI", days)


def fetch_macro_snapshot() -> dict[str, float]:
    """Return latest macro feature values (oil, iron ore proxy, VIX, DXY, etc.)."""
    result: dict[str, float] = {}
    try:
        tickers = list(MACRO_TICKERS.values())
        raw = yf.download(tickers, period="5d", interval="1d", progress=False, auto_adjust=True)
        if not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                last = raw["Close"].iloc[-1]
            else:
                last = raw["Close"].iloc[-1]
            for name, yt in MACRO_TICKERS.items():
                val = last.get(yt) if hasattr(last, "get") else None
                if val is not None and not pd.isna(val):
                    result[name] = float(val)
    except Exception as e:
        log.warning("macro_fetch_failed", error=str(e))
    return result


def get_current_rates() -> dict[str, float]:
    """Get current rate index values.

    Returns dict with BDI, BDTI, BCTI etc.
    Uses FRED for BDI/BDTI if key available, else returns recent synthetic values.
    """
    rates = dict(SYNTHETIC_RATES)

    # Try to get BDI from FRED
    bdi_hist = fetch_bdi_history(days=10)
    if not bdi_hist.empty:
        rates["BDI"] = float(bdi_hist.iloc[-1].values[0])

    bdti_hist = fetch_bdti_history(days=10)
    if not bdti_hist.empty:
        rates["BDTI"] = float(bdti_hist.iloc[-1].values[0])

    return rates


def get_rate_momentum(index_name: str, lookback_days: int = 90) -> float:
    """Return percentage change in rate index over lookback period.

    Returns float (e.g. 12.5 means +12.5%).
    Falls back to 0.0 if data unavailable.
    """
    fred_map = {"BDI": "BDIY", "BDTI": "BDTI"}
    series_id = fred_map.get(index_name)
    if series_id:
        df = _fred_fetch(series_id, days=lookback_days + 10)
        if len(df) >= 2:
            old = float(df.iloc[0].values[0])
            new = float(df.iloc[-1].values[0])
            if old > 0:
                return (new - old) / old * 100
    return 0.0
