"""Fetch intraday and historical stock prices via yfinance."""

import pandas as pd
import yfinance as yf
import structlog

from src.config.universe import TICKERS, TICKER_MAP

log = structlog.get_logger()

# NOK/USD approximate rate (updated manually; could be fetched live)
NOK_USD = 0.094


def _to_usd(price: float, currency: str) -> float:
    """Convert price to USD if needed."""
    if currency == "NOK":
        return price * NOK_USD
    return price


def fetch_current_prices(tickers: list[str] | None = None) -> pd.DataFrame:
    """Return latest price snapshot for all tickers, falling back to per-ticker fetch."""
    tickers = tickers or TICKERS
    log.info("fetching_prices", count=len(tickers))

    # Try batch download first
    rows = []
    try:
        raw = yf.download(tickers, period="2d", interval="1h", progress=False, auto_adjust=True)
        if not raw.empty and isinstance(raw.columns, pd.MultiIndex):
            close_df = raw["Close"]
            for t in tickers:
                if t in close_df.columns:
                    series = close_df[t].dropna()
                    if len(series) >= 2:
                        price = float(series.iloc[-1])
                        prev  = float(series.iloc[-2])
                        currency = TICKER_MAP[t].currency if t in TICKER_MAP else "USD"
                        price_usd = _to_usd(price, currency)
                        prev_usd  = _to_usd(prev, currency)
                        rows.append({
                            "ticker": t,
                            "price": price_usd,
                            "prev_close": prev_usd,
                            "change_pct": (price_usd - prev_usd) / prev_usd * 100,
                        })
    except Exception as e:
        log.warning("batch_price_failed", error=str(e))

    fetched = {r["ticker"] for r in rows}
    missing  = [t for t in tickers if t not in fetched]

    # Per-ticker fallback for any that failed
    for t in missing:
        try:
            d = yf.download(t, period="5d", progress=False, auto_adjust=True)
            if not d.empty:
                series = d["Close"].dropna()
                if len(series) >= 2:
                    price = float(series.iloc[-1])
                    prev  = float(series.iloc[-2])
                    currency = TICKER_MAP[t].currency if t in TICKER_MAP else "USD"
                    price_usd = _to_usd(price, currency)
                    prev_usd  = _to_usd(prev, currency)
                    rows.append({
                        "ticker": t,
                        "price": price_usd,
                        "prev_close": prev_usd,
                        "change_pct": (price_usd - prev_usd) / prev_usd * 100,
                    })
                    log.info("per_ticker_fallback_ok", ticker=t)
        except Exception as e2:
            log.warning("per_ticker_price_failed", ticker=t, error=str(e2))

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def fetch_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Return daily OHLCV history for a single ticker."""
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        df.index.name = "date"
        return df.reset_index()
    except Exception as e:
        log.error("price_history_failed", ticker=ticker, error=str(e))
        return pd.DataFrame()


def fetch_batch_history(tickers: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Return daily close history for multiple tickers."""
    try:
        raw = yf.download(tickers, period=period, progress=False, auto_adjust=True)
        if raw.empty:
            return {}
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            close = raw[["Close"]].rename(columns={"Close": tickers[0]})
        return {t: close[[t]].rename(columns={t: "close"}).dropna() for t in close.columns}
    except Exception as e:
        log.error("batch_history_failed", error=str(e))
        return {}
