# Stack Research: Shipping Stock Dashboard

## Recommended Stack

| Component | Library | Version | Rationale |
|---|---|---|---|
| Web framework | streamlit | 1.58.0 | Native Python, zero-JS, free Community Cloud hosting, built-in caching primitives |
| Data manipulation | pandas | 3.0.3 | Core timeseries handling; required ≥ Python 3.11 |
| Price data | yfinance | 1.4.1 | De-facto standard for Yahoo Finance OHLCV; covers US + European ADRs and local tickers (e.g. MAERSK-B.CO, ZIM, CMRE) |
| Macro/BDI data | fredapi | 0.5.2 | Thin official FRED wrapper; cleaner than pandas-datareader for FRED-only use |
| ML boosting | xgboost | 3.2.0 | Best-in-class gradient boosting; native feature importance; ships wheels for Python 3.10–3.14 |
| ML baseline/pipeline | scikit-learn | 1.9.0 | Preprocessing pipelines, cross-validation, scalers; integrates cleanly with XGBoost |
| Rate forecasting | statsmodels | 0.14.6 | SARIMA via `statsmodels.tsa.statespace.sarimax.SARIMAX`; supports exogenous regressors (macro BDI inputs) |
| Visualization | plotly | 5.x (latest) | Interactive candlestick, scatter, bar; `st.plotly_chart` is native in Streamlit |
| Background scheduling | APScheduler | 3.11.2 | `BackgroundScheduler` for intraday refresh inside a long-lived Streamlit process; caveat below |
| Persistence | parquet (via pandas) + GitHub commit | — | See Persistence section |
| Secrets | st.secrets / TOML | — | Community Cloud native |

---

## Data Layer

### Price data — yfinance 1.4.1
- `yf.download(tickers, period, interval)` supports 1m–60m intraday (15-day rolling window for sub-1h intervals).
- European tickers: use Yahoo suffixes (`.CO`, `.OL`, `.ST`, `.PA`, `.AS`, `.L`).
- Wrap all yfinance calls with `@st.cache_data(ttl=900)` (15-min TTL) to avoid hammering Yahoo.
- Rate-limit guard: add `time.sleep(0.2)` between ticker batches in loops.

### Macro / BDI rates — fredapi 0.5.2 + direct FRED API
- `fredapi.Fred(api_key=st.secrets["FRED_API_KEY"])` then `.get_series("DCOILWTICO")`.
- BDI on FRED: series `BDIY` (Baltic Dry Index, daily). Alternatively scrape from `data.nasdaq.com` (Quandl successor) using `requests`; the Quandl Python package is deprecated — use REST directly.
- `pandas-datareader` (0.10.0) is **not recommended**: maintenance has stalled since 2023; most non-FRED sources are broken. Use fredapi for FRED and yfinance for price data instead.

### SEC 20-F fleet data
- No dedicated Python library. Use `requests` + `sec-api` (unofficial, has free tier) or scrape EDGAR full-text search API (`efts.sec.gov/LATEST/search-index?q=...&dateRange=custom`).
- Parse 20-F filings annually; cache results as a static parquet file committed to the repo (fleet data changes at most quarterly).

---

## ML / Modeling Layer

### XGBoost price model
- `xgboost.XGBRegressor` with `tree_method="hist"` (CPU-friendly on Community Cloud).
- Feature set: BDI lag features, macro regressors, fleet utilization proxy, momentum indicators computed with `ta-lib` or pure pandas.
- Walk-forward validation via `sklearn.model_selection.TimeSeriesSplit`.

### SARIMA rate forecast
- `statsmodels.tsa.statespace.sarimax.SARIMAX(endog=bdi_series, order=(p,d,q), seasonal_order=(P,D,Q,52))`.
- Fit weekly BDI; use `.forecast(steps=N)` for forward rate scenarios feeding the NAV engine.
- Cache fitted model object with `@st.cache_resource` (model is not data, not serializable via `cache_data` without extra work).

### NAV / FCF engine
- Pure pandas: DCF with scenario matrix (bull/base/bear) driven by SARIMA forecast quantiles.
- No additional library needed beyond `numpy` + `pandas`.

### Composite score
- `sklearn.preprocessing.MinMaxScaler` to normalize sub-scores before weighted sum.
- Weights configurable via `st.sidebar.slider` at runtime.

---

## Persistence

### The core constraint
Streamlit Community Cloud's filesystem is **ephemeral**: any file written at runtime (SQLite, parquet, pickle) is lost on app restart or sleep/wake cycle. Community Cloud apps sleep after ~7 days of inactivity and are rebuilt from scratch on redeploy.

### Recommended pattern: parquet files committed to GitHub

1. Run a **GitHub Actions cron workflow** (e.g. `schedule: cron: '0 6 * * *'`) that:
   - Fetches daily fundamentals (FRED macro, SEC fleet snapshot)
   - Writes to `data/daily_cache.parquet` in the repo
   - Auto-commits and pushes to `main`
2. The Streamlit app reads `data/daily_cache.parquet` directly from the repo at startup with `pd.read_parquet("data/daily_cache.parquet")` — no external DB needed.
3. Intraday prices (yfinance, 15–60 min TTL) stay purely in-memory via `@st.cache_data(ttl=900)` — they are always re-fetchable and don't need disk persistence.

### Why not SQLite
- SQLite written at runtime is wiped on restart. You could store it in the repo via the same GitHub Actions pattern, but binary git blobs for databases cause repo bloat and merge conflicts. Parquet is columnar, smaller, and diff-friendly.

### Why not external DB (Postgres, Supabase, etc.)
- Adds cost and operational complexity for a personal research tool. Parquet-in-repo is sufficient for daily fundamentals; intraday data is never persisted anyway.

### st.cache_data persistence parameter
- `@st.cache_data(persist="disk")` writes a pickle to `~/.streamlit/cache` — this path is also ephemeral on Community Cloud. **Do not rely on it for cross-session persistence.**

---

## Deployment Notes (Streamlit Community Cloud)

### Setup
- Connect GitHub repo → Community Cloud auto-deploys on push to configured branch.
- `requirements.txt` (or `pyproject.toml`) must list all dependencies with pinned versions. Use `pip freeze > requirements.txt` locally to generate.
- Python version: specify in `.python-version` file or `[tool.python]` section; Community Cloud supports all security-maintained CPython releases. Target **Python 3.11** (pandas 3.x minimum).

### Secrets
- Dashboard at share.streamlit.io → App settings → Secrets tab.
- Paste TOML: `FRED_API_KEY = "..."`, `QUANDL_KEY = "..."`.
- Access in code: `st.secrets["FRED_API_KEY"]`.
- Local dev: `.streamlit/secrets.toml` (never commit; add to `.gitignore`).

### Background refresh (APScheduler caveat)
- `APScheduler.BackgroundScheduler` runs in a daemon thread within the Streamlit process. On Community Cloud, the process is shared across sessions; this is fine for polling yfinance every 15 min.
- Known issue: APScheduler threads do not have a Streamlit `ReportContext`; they **cannot call `st.*` functions** directly. Pattern: scheduler writes to a module-level dict or a temporary file; the Streamlit render loop reads from it via `st.cache_data` or polling with `st.rerun()`.
- Alternative simpler pattern: use `st.cache_data(ttl=900)` without APScheduler — Streamlit auto-refreshes stale cache on next user interaction. For true background push, APScheduler is needed but adds complexity.
- Community Cloud does not run background processes when the app is sleeping (no active user). This is acceptable for a personal tool.

### Resource limits
- Community Cloud free tier: ~1 GB RAM, 1 CPU, apps sleep after inactivity. XGBoost training on historical data (a few years, ~15 tickers) is fine within 1 GB if done offline or at startup. Do not retrain on every rerun — use `@st.cache_resource` for trained models.

### Rate limiting from GitHub
- Community Cloud rate-limits GitHub webhook triggers to 5/min. Not relevant for this project's deploy cadence.

---

## Alternatives Considered

| Framework | Verdict | Reason not chosen |
|---|---|---|
| **Dash (Plotly)** | Skip | More boilerplate (callbacks, layout components); requires understanding React-like state model; no free managed hosting equivalent to Community Cloud |
| **Panel (HoloViz)** | Skip | Excellent for complex dashboards but steeper learning curve; no free hosting story as clean as Streamlit Community Cloud |
| **Gradio** | Skip | Designed for ML model demos, not multi-page financial dashboards; poor support for custom data tables and multi-chart layouts |
| **Marimo** | Monitor | Reactive notebook alternative to Streamlit; promising but ecosystem smaller and Community Cloud equivalent not available yet (as of mid-2025) |
| **Quandl/Nasdaq Data Link Python** | Skip | Official Quandl Python package deprecated; use direct REST API for Nasdaq Data Link, or FRED via fredapi for macro series |
| **pandas-datareader** | Skip | Maintenance stalled; most data sources broken except FRED which fredapi covers better |

---

## Confidence Levels

| Recommendation | Confidence | Notes |
|---|---|---|
| Streamlit 1.58.0 | High | Latest stable; Community Cloud always supports current release |
| yfinance 1.4.1 | High | Dominant choice; no viable alternative for free Yahoo Finance data |
| fredapi 0.5.2 | High | Official FRED wrapper; stable API |
| XGBoost 3.2.0 | High | Mature; GPU not needed for this scale |
| statsmodels 0.14.6 (SARIMA) | High | Gold standard for classical time-series in Python |
| scikit-learn 1.9.0 | High | Stable; no concerns |
| plotly for charts | High | Best interactive charts in Streamlit ecosystem |
| Parquet-in-repo for daily data | Medium | Works well for personal use; breaks if data volume grows beyond ~50 MB or update frequency increases; migrate to Supabase free tier if needed |
| APScheduler for intraday refresh | Medium | Works but has the ReportContext limitation; simpler TTL-based caching may be sufficient depending on UX requirements |
| SEC 20-F via EDGAR REST | Medium | EDGAR API is free but undocumented edge cases; fleet data extraction may require manual regex tuning per filing format |
| Quandl/Nasdaq Data Link via REST | Low-Medium | BDI on FRED (`BDIY`) is the more reliable source; Nasdaq Data Link REST is a fallback if FRED BDI lags |
