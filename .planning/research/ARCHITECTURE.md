# Architecture Research: Shipping Stock Dashboard

## Component Map

### 1. Data Ingestion Layer (`src/ingestion/`)
Responsible for fetching raw data from all external sources. Each source is a standalone module with its own retry/caching logic. No model code here.

- `yfinance_fetcher.py` — intraday OHLCV for shipping tickers (SBLK, GOGL, ZIM, etc.)
- `fred_fetcher.py` — BDI, BDIY, T2YY, FEDFUNDS, DXY daily series via `fredapi`
- `sec_loader.py` — parses 20-F XML/HTML for fleet count, DWT, utilization (manual v1 = static JSON fallback)
- `cache.py` — thin wrapper: reads from local parquet/SQLite first, hits API only on cache miss or stale TTL

Boundary rule: ingestion modules return typed DataFrames and write nothing to UI state. They do not call model code.

### 2. Model Layer (`src/models/`)
Pure computation; no I/O except reading from the cache written by ingestion.

- `rate_forecast.py` — SARIMA baseline + XGBoost residual correction; outputs 30/60/90-day BDI forward curves
- `nav_engine.py` — fleet NAV: vessel count × avg vessel value (sourced from Clarksons proxies or 20-F DWT), net of debt
- `fcf_scenarios.py` — bull/base/bear FCF per share across rate curve scenarios
- `composite_scorer.py` — weighted rank of NAV discount, FCF yield, rate momentum, debt/EBITDA; outputs 0–100 score per ticker

Boundary rule: every model function is a pure `DataFrame → DataFrame` transform. No `st.*` calls, no file I/O.

### 3. Persistence Layer (`src/persistence/`)
Bridges the ephemeral Streamlit filesystem and durable storage.

- `store.py` — read/write interface; abstracts backend (local parquet in dev, Supabase Postgres in prod)
- `schema.py` — table definitions and DataFrame→SQL mappers

### 4. Dashboard Layer (`src/dashboard/`)
Streamlit app. Reads only from the persistence/cache layer; never calls APIs directly.

- `app.py` — entrypoint, page routing
- `pages/overview.py` — composite score leaderboard
- `pages/ticker.py` — single-ticker deep-dive (NAV waterfall, FCF scenarios, rate chart)
- `pages/rates.py` — BDI + macro panel

Boundary rule: dashboard code only calls `store.read_*()` functions and renders. All computation happened upstream.

### 5. Orchestration Layer (outside `src/`)
- `.github/workflows/refresh_intraday.yml` — 15-min GitHub Actions cron
- `.github/workflows/refresh_daily.yml` — 06:00 UTC daily cron
- Each workflow: fetch → model → write to Supabase → (optionally commit summary parquet to repo)

---

## Data Flow

```
[yfinance]  15-min tick
     │
     ▼
ingestion/yfinance_fetcher.py
     │  returns OHLCV DataFrame
     ▼
ingestion/cache.py  ──────── writes ──────► Supabase: prices table
     │  reads back clean OHLCV
     ▼
models/rate_forecast.py
     │  BDI forward curve (30/60/90d)
     ▼
models/nav_engine.py  ◄──── SEC 20-F static JSON (fleet data)
     │  NAV per share
     ▼
models/fcf_scenarios.py
     │  FCF bull/base/bear × ticker
     ▼
models/composite_scorer.py
     │  score 0-100 per ticker
     ▼
persistence/store.py  ───── writes ──────► Supabase: scores table
     │
     ▼  (Streamlit session reads from Supabase)
dashboard/pages/overview.py  →  user sees leaderboard
dashboard/pages/ticker.py    →  user drills into NAV/FCF
```

Daily fundamentals (FRED BDI, macro) follow the same path but run on the daily cron only.

---

## Refresh Architecture

### The Core Problem
Streamlit Community Cloud runs a single Python process per user session. It has no persistent background threads between sessions and no cron primitives. `APScheduler` inside the Streamlit process is unreliable: it dies when the session times out and duplicate instances spawn per user.

### Recommended Solution: GitHub Actions as External Scheduler

**Intraday refresh (every 15 minutes, market hours)**
```yaml
# .github/workflows/refresh_intraday.yml
on:
  schedule:
    - cron: '*/15 13-21 * * 1-5'   # 09:00–17:00 ET in UTC
jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements-ci.txt
      - run: python scripts/run_intraday.py   # fetch → model → write Supabase
    env:
      SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
      SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
      FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
```

GitHub Actions free tier gives 2,000 minutes/month. 15-min cron during 8 market hours × 5 days × ~4 weeks = ~640 runs/month × ~1 min each = ~640 minutes. Fits within free tier.

**Daily refresh (fundamentals + forecast refit)**
```yaml
on:
  schedule:
    - cron: '0 6 * * 1-5'    # 06:00 UTC, before market open
```
Runs SARIMA/XGBoost refit, SEC data reload, full score recompute. Writes to Supabase.

**Streamlit session behavior**
On page load, `store.read_scores()` pulls the latest rows from Supabase. No refresh logic inside Streamlit itself. Optionally add a "Last updated: X minutes ago" indicator from the `updated_at` column.

### Why Not APScheduler in Streamlit?
- Session timeout = scheduler dies silently
- Multiple users = multiple scheduler instances, duplicate API calls and rate limits
- No guarantee of execution between sessions (if no user is active, nothing refreshes)

### Why Not GitHub Actions Writing Parquet to Repo?
- Works for daily data (1 commit/day is fine)
- Breaks for 15-min intraday: 32+ commits/day pollutes git history, risks Actions throttling, and creates merge conflicts if the repo has any other activity
- Acceptable only as a fallback if Supabase is avoided entirely

---

## Persistence Strategy

### Recommended: Supabase Free Tier (Postgres)

Supabase free tier provides 500 MB Postgres, up to 50,000 rows, and a Python client (`supabase-py`). It survives between Streamlit sessions and between GitHub Actions runs.

**Tables:**
```sql
prices (ticker TEXT, ts TIMESTAMPTZ, open FLOAT, high FLOAT, low FLOAT, close FLOAT, volume BIGINT)
rates  (series TEXT, date DATE, value FLOAT)          -- BDI, FRED macro
scores (ticker TEXT, computed_at TIMESTAMPTZ, nav_per_share FLOAT, fcf_base FLOAT, composite_score FLOAT)
fleet  (ticker TEXT, loaded_at DATE, vessel_count INT, dwt_total FLOAT, net_debt FLOAT)
```

Streamlit reads via `supabase.table("scores").select("*").order("composite_score", desc=True).execute()`. No local state needed between sessions.

**Credentials:** stored as Streamlit secrets (`st.secrets["SUPABASE_URL"]`) and GitHub Actions secrets. Same env vars work in both contexts.

### Fallback: Google Sheets as DB

If Supabase adds friction, `gspread` + a service account writes to Google Sheets. Sheets has a 10M cell limit and ~1-2s write latency; fine for daily fundamentals, borderline for 15-min intraday across 10 tickers. Use only if Supabase is unavailable.

### Dev-only: Local Parquet Cache

During development, `ingestion/cache.py` writes `.cache/prices_{ticker}.parquet` and reads from there first. This avoids API calls during UI iteration. The cache directory is `.gitignore`d. On Streamlit Cloud, this cache is cold on every deploy — all reads fall through to Supabase.

---

## Recommended Build Order

### Phase 1: Data Pipeline (foundation — nothing else works without this)
1. `ingestion/yfinance_fetcher.py` — pull intraday for 3 tickers, verify shape
2. `ingestion/fred_fetcher.py` — pull BDI, verify daily series
3. `ingestion/cache.py` — local parquet read/write with TTL
4. Supabase schema + `persistence/store.py` read/write methods
5. `scripts/run_intraday.py` and `scripts/run_daily.py` — headless runner scripts
6. GitHub Actions workflows wired to secrets — verify a real write lands in Supabase

**Gate before Phase 2:** Supabase has live data. `store.read_prices("SBLK")` returns a non-empty DataFrame.

### Phase 2: Model Layer
1. `models/rate_forecast.py` — SARIMA baseline first (deterministic, no tuning); XGBoost residual second
2. `models/nav_engine.py` — static 20-F JSON as input v1; replace with live parsing later
3. `models/fcf_scenarios.py` — parameterized bull/base/bear against rate curve
4. `models/composite_scorer.py` — weighted rank; weights as config constants, not hardcoded

**Gate before Phase 3:** `composite_scorer.py` returns a clean DataFrame with one row per ticker. Supabase `scores` table has fresh rows after a manual `python scripts/run_daily.py`.

### Phase 3: Dashboard
1. `dashboard/app.py` — skeleton with page routing
2. `pages/overview.py` — scores leaderboard (table + bar chart)
3. `pages/rates.py` — BDI time series + FRED macro panel
4. `pages/ticker.py` — NAV waterfall, FCF scenario chart, price chart

**Gate before deploy:** app runs locally against Supabase prod data with no errors.

### Phase 4: Streamlit Cloud Deploy
1. Push repo, connect to Streamlit Community Cloud
2. Add secrets via Streamlit Cloud UI
3. Verify cold-start reads from Supabase correctly (no local cache)
4. Confirm GitHub Actions cron fires and data updates appear in dashboard within 20 min

---

## Key Architectural Risks

### 1. GitHub Actions Free Tier Exhaustion
15-min cron year-round = ~35,000 minutes/year. Free tier is 2,000 minutes/month (24,000/year). **Risk: overrun in month 2.** Mitigations: restrict cron to market hours only (saves ~65%), or move to a free external scheduler (cron-job.org hitting a GitHub Actions webhook trigger) that doesn't consume Actions minutes.

### 2. yfinance Rate Limiting
yfinance scrapes Yahoo Finance with no official API contract. Yahoo has silently broken yfinance multiple times. **Risk: intraday fetch silently returns empty or stale data.** Mitigation: always check `df.empty` and `df.index.max() > now - 30min` before writing to Supabase; alert via a GitHub Actions step failure email.

### 3. Supabase Free Tier Suspension
Supabase pauses free projects after 1 week of inactivity. **Risk: project paused over a long weekend, dashboard shows stale data.** Mitigation: GitHub Actions daily ping to Supabase keeps it active; alternatively upgrade to Pro ($25/mo) if the project becomes relied upon.

### 4. SARIMA Refit Cost on Actions
SARIMA refit on 2+ years of BDI daily data with auto-order selection (`pmdarima`) can take 3–8 minutes. Combined with XGBoost, daily refit may hit the 6-minute GitHub Actions job timeout. **Risk: daily forecast never completes.** Mitigation: pre-select SARIMA order once and hardcode (p,d,q)(P,D,Q,m); only refit order monthly. Cache the fitted model as a joblib pickle in Supabase storage or as a repo artifact.

### 5. SEC 20-F Parsing Brittleness
20-F HTML structure varies by company and filing year. **Risk: fleet data silently goes stale or breaks.** Mitigation: v1 is a manually maintained `data/fleet_static.json` updated quarterly. This is the correct v1 approach — don't automate SEC parsing until the model is proven valuable.

### 6. Streamlit Session State vs. Supabase Freshness
Streamlit caches data with `@st.cache_data(ttl=900)`. If a user keeps a tab open across a cron cycle, they see stale scores. This is acceptable for personal use but worth noting — a manual "Refresh" button calling `st.cache_data.clear()` resolves it trivially.

### 7. Model Overfitting Risk (XGBoost on BDI)
BDI is a noisy, regime-switching series. XGBoost on lagged BDI features will overfit to recent regimes without walk-forward validation. **Risk: forecast looks good in backtests, fails live.** Mitigation: enforce a time-series cross-validation split in `rate_forecast.py` from day one; log `val_rmse` to Supabase so degradation is visible on the dashboard.
