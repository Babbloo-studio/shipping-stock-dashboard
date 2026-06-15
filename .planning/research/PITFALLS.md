# Pitfalls Research: Shipping Stock Dashboard

## Data Pitfalls

### DP-1 yfinance Data Gaps and Stale Prices for Thinly Traded European Stocks
**What goes wrong:** yfinance pulls last-trade prices, not bid/ask midpoints. For thinly traded European shippers (e.g. Oslo-listed HAFNI, Athens-listed stocks), days can pass between trades. The last-close field silently holds a week-old price, displaying as "today's" value.

**Warning signs:**
- Volume = 0 on many days for small-cap names
- `info["previousClose"]` matches `info["currentPrice"]` across multiple calendar days
- Oslo Børs closes at 16:20 CET; UTC offset causes yfinance to misattribute the trading day on end-of-day pulls

**Prevention:**
- Flag any stock where rolling 5-day average volume < 1,000 shares with a STALE_PRICE badge
- Compare `lastTradeDate` to system date; warn if gap > 1 business day
- For European tickers, always append the correct suffix (`.OL` Oslo, `.AT` Athens, `.L` London) — omitting suffix silently falls back to a US OTC pink-sheet quote

---

### DP-2 Baltic Dry Index Series Breaks and Holiday Gaps
**What goes wrong:** The BDI is published on London business days only. Weekends + UK bank holidays produce NaN gaps. Naively forward-filling NaN for two weeks around Christmas (UK closes early) creates an artificially flat rate signal that then triggers a false breakout detection when trading resumes.

**Warning signs:**
- BDI series has 0 or NaN for more than 3 consecutive days outside known holiday windows
- FRED `BDIY` series lags the Baltic Exchange by 1–2 days and is updated irregularly

**Prevention:**
- Maintain an explicit UK bank holiday calendar; distinguish "expected gap" from "data feed failure"
- Forward-fill only up to 3 business days; beyond that, mark the gap explicitly and suppress rate-forecast outputs for that window
- Cross-check BDI against Clarksons spot indices if available; divergence > 10% signals a stale feed

---

### DP-3 Survivorship Bias in Stock Universe
**What goes wrong:** Building the ticker list from current major-index constituents (e.g. current S&P Shipping ETF holdings) excludes companies that went bankrupt, were acquired, or delisted during the sample period. Backtesting NAV accuracy against this clean universe inflates apparent model quality.

**Warning signs:**
- All historical NAV estimates are positive (no negative-equity cases in sample)
- Backtest Sharpe ratios are implausibly high (> 2.5 annualized over a full cycle)

**Prevention:**
- Maintain a static, versioned universe file (`universe.yaml`) that includes delisted tickers with their delisting dates and reason
- For backtesting, snapshot the universe as it existed at each point in time
- Mark tickers with < 24 months of trading history as "insufficient history" rather than excluding them silently

---

### DP-4 Currency Mismatch — European Stocks Reported in Local Currency
**What goes wrong:** Norwegian shippers (e.g. Golden Ocean, Frontline) report financials in USD but trade on Oslo Børs in NOK. yfinance returns price in NOK; SEC 20-F equivalents filed on Oslo Børs use USD for financials. Mixing currencies in the same NAV engine without explicit conversion produces nonsense per-share values.

**Warning signs:**
- P/NAV ratios for Norwegian stocks are ~10x those for US-listed peers
- Price-to-book multiples show as 0.01x or 100x rather than the typical 0.5–2.0x range

**Prevention:**
- Store a `reporting_currency` and `trading_currency` field per ticker in `universe.yaml`
- Always pull the USD/NOK, USD/EUR, USD/GBP exchange rate for the same date as the financial snapshot
- Assert that P/NAV for every name falls between 0.2x and 5.0x before displaying; log and suppress otherwise

---

### DP-5 SEC 20-F Parsing Failures
**What goes wrong:** Foreign private issuers file 20-Fs rather than 10-Ks. Many European shippers file 20-F as an HTML/XML hybrid with non-standard XBRL tagging. Regex-based scrapers that work on 10-K filings silently return NaN for key line items (fleet value, debt maturity schedule).

**Warning signs:**
- Total assets parsed from 20-F is < 50% of the value reported in an investor presentation for the same period
- Long-term debt field is zero for a company with known credit facility

**Prevention:**
- Validate every parsed 20-F against at least two balance-sheet identity checks: `assets = liabilities + equity` (±1%), and total fleet book value < total assets
- Log the SEC accession number and the specific XBRL tag path used; surface this in a data-provenance panel

---

## Model Pitfalls

### MP-1 NAV from Book Value Instead of Secondhand Market Value
**What goes wrong:** Book value of vessels is historical cost minus accumulated depreciation. A 10-year-old Capesize bought in 2014 at a peak market price may be carried at $15M book but trade at $8M secondhand today — or vice versa in a hot market. NAV computed from book value produces P/NAV ratios that are directionally inverted from actual fleet replacement value.

**Warning signs:**
- Company's reported book value per share is stable across a cyclical downturn while vessel values collapsed 40%
- P/NAV > 1.0x during a severe oversupply period (impossible if NAV reflects true fleet value)

**Prevention:**
- Use Baltic secondhand vessel price indices (Clarksons, VesselsValue API if budget allows; otherwise scrape S&P brokers' public market reports) as the primary fleet valuation input
- Apply depreciation only as a cross-check, not as the primary value estimate
- Clearly label the NAV estimate as "market-value NAV" vs "book-value NAV" in all displayed outputs

---

### MP-2 Ignoring Charter Coverage When Computing FCF
**What goes wrong:** A company with 80% of its fleet on fixed time charters at above-market rates has a very different FCF profile than a spot-exposed peer, even if both have identical fleets. Projecting FCF from current spot rates without subtracting existing charter commitments (or adding charter premium) produces wrong scenario outputs.

**Warning signs:**
- FCF for a company with disclosed long-term charters shows high variance identical to spot-exposed peers
- Dividend coverage ratio implied by the model differs by > 30% from management guidance

**Prevention:**
- Parse the "Fleet and Employment" table from each 20-F to extract charter coverage percentage and weighted average remaining duration
- Model FCF in two components: (1) fixed-rate contracted revenue × coverage%, (2) spot-rate revenue × (1 − coverage%)
- Flag companies with > 50% spot exposure as HIGH_SPOT_RISK in the composite score breakdown

---

### MP-3 Conflating Sub-Sectors (Dry Bulk Rates Do Not Predict Tanker Prices)
**What goes wrong:** The BDI tracks dry bulk (grain, iron ore, coal). Crude tanker rates follow the BDTI (Baltic Dirty Tanker Index); product tanker rates follow the BCTI. LNG and LPG have entirely separate rate benchmarks tied to Henry Hub spreads and LPG arbitrage windows. Using BDI as a proxy for the whole shipping market in the rate-forecast model corrupts signals for non-dry-bulk names.

**Warning signs:**
- Model assigns the same rate-forecast signal to a VLCC tanker company as to a Capesize dry bulk company
- Rate correlation between model input and a tanker company's reported TCE is < 0.3

**Prevention:**
- Tag every ticker with its primary sub-sector: `dry_bulk`, `crude_tanker`, `product_tanker`, `container`, `lng`, `lpg`, `car_carrier`, `offshore`
- Load the appropriate rate index for each sub-sector; never use BDI for non-dry-bulk names
- The XGBoost rate-forecast model must be trained and evaluated separately per sub-sector, not on a pooled dataset

---

### MP-4 Overfitting Rate Forecast to Recent Cycle
**What goes wrong:** Training the SARIMA/XGBoost model on data since 2020 captures an extreme COVID demand shock, the 2021–2022 container super-cycle, and the 2022–2023 tanker spike. A model fitted to this window will learn these step-changes as "normal" seasonal patterns and overestimate rate persistence.

**Warning signs:**
- Out-of-sample MAPE on 2018–2019 data (a neutral period) is > 40% while in-sample MAPE is < 10%
- The model always predicts mean reversion toward 2021-level rates rather than long-run historical averages

**Prevention:**
- Train on at least 20 years of data where available (BDI history goes back to 1985)
- Reserve 2018–2019 as a held-out validation set; evaluate model performance on this period explicitly
- Include long-run fleet supply variables (orderbook-to-fleet ratio, scrapping age) as exogenous regressors; these constrain rate levels to physical fundamentals

---

### MP-5 Using GAAP EPS Instead of TCE-Based Metrics
**What goes wrong:** GAAP EPS includes non-cash items (vessel impairments, mark-to-market on interest rate swaps, unrealized FX gains/losses) that can swing earnings 50–200% without affecting cash generation. Shipping equities are universally valued on TCE (time charter equivalent) revenue and daily EBITDA per vessel, not GAAP EPS.

**Warning signs:**
- A company reports negative GAAP EPS but is paying a substantial dividend (common in impairment years)
- P/E ratio shows as negative or > 100x while the company appears undervalued by any operator metric

**Prevention:**
- Compute TCE = (revenue − voyage costs) / operating days for each vessel class where 20-F data allows
- Present TCE/day and EV/EBITDA as the primary valuation metrics; relegate GAAP EPS to a footnote
- When TCE is not parseable from filings, use reported "net revenue" or "operating revenue after voyage costs" as the closest available proxy

---

### MP-6 Ignoring Drydock Schedule in FCF Projections
**What goes wrong:** Vessels must enter drydock for regulatory surveys every 2.5 years (intermediate) and 5 years (special survey). Off-hire during drydock (typically 2–4 weeks) plus drydock capex ($0.5M–$3M depending on vessel size) can reduce annual FCF by 5–15% in a drydock-heavy year. Ignoring this produces upward-biased FCF in peak-drydock years.

**Warning signs:**
- FCF model implies a steady payout ratio but the company's actual dividend was cut in years with disclosed major drydocks
- Fleet age distribution shows many vessels built in the same 2–3 year window, implying synchronized drydock peaks

**Prevention:**
- Parse fleet list and build dates from 20-F fleet tables; compute each vessel's 5-year survey cycle
- Model drydock capex as $1.5M/vessel (default, adjustable per size class) in the applicable years
- Apply a 3.5% off-hire assumption per drydock event to reduce revenue in those periods

---

## Infrastructure Pitfalls (Streamlit Cloud)

### IP-1 App Sleeping Loses Cached Rate Data
**What goes wrong:** Streamlit Community Cloud sleeps apps after ~7 days of inactivity (sooner under load). When the app wakes, `st.cache_data` memory caches are empty. If the app fetches fresh data from yfinance or FRED on wake and those services return errors (rate limits, network blip), the app either crashes or displays "No data available" with no explanation.

**Warning signs:**
- Users report the app shows "Loading..." indefinitely on first visit
- Error logs show `RemoteDataError` or `JSONDecodeError` on cache miss paths

**Prevention:**
- Cache all fetched data to a JSON or Parquet file in the project repo (committed, not ephemeral) as a fallback; use this if the live fetch fails
- Set `st.cache_data(ttl=3600)` and always return the last-known-good value on exception, with a visible "Data as of [timestamp]" warning
- Never make the app uncacheable on the critical render path; pre-fetch all data in a background job and store in the repo if Streamlit Cloud scheduled runs are available

---

### IP-2 Ephemeral Filesystem Wiping SQLite or Parquet Caches
**What goes wrong:** Files written to the Streamlit Cloud container filesystem (e.g. a local SQLite cache, a downloaded CSV) are wiped on every app restart or sleep-wake cycle. Any architecture that writes to disk at runtime and reads it back later will silently break after the first sleep.

**Warning signs:**
- Cache appears warm after the first user session but empty after the app restarts overnight
- SQLite "no such table" errors in logs after a deploy or sleep event

**Prevention:**
- Treat the Streamlit Cloud filesystem as read-only ephemeral storage; never persist state there
- Store all cached data in the Git repository as committed static files updated by a GitHub Actions workflow, or use an external service (e.g. Supabase free tier, GitHub Releases as a data artifact store)
- Document this constraint explicitly in `ARCHITECTURE.md` to prevent future developers from re-introducing local writes

---

### IP-3 Secrets Leaking in Public Repository
**What goes wrong:** API keys (FRED API key, any paid data vendor token) hardcoded in source or committed in a `.env` file that was accidentally staged. Streamlit's `st.secrets` mechanism is the correct approach, but the secrets TOML file must be in `.gitignore` from day one.

**Warning signs:**
- `.env` file appears in `git status` output
- `secrets.toml` was committed even once (git history retains it even after deletion)

**Prevention:**
- Add `.env`, `secrets.toml`, `.streamlit/secrets.toml` to `.gitignore` before the first commit
- Run `git log --all --full-history -- "*.env" "*.toml"` periodically to verify no secret file was ever committed
- Use only `st.secrets["FRED_API_KEY"]` in code; never `os.environ.get("FRED_API_KEY")` without a documented fallback

---

### IP-4 Streamlit Community Cloud Free-Tier Rate Limits
**What goes wrong:** The free tier imposes resource limits that are not well-documented. Apps making many outbound HTTP requests (fetching 30+ tickers × multiple yfinance calls) can trigger timeouts or cause the app to OOM-crash on Streamlit's infrastructure, producing a generic "Something went wrong" error.

**Warning signs:**
- App works locally but times out on Streamlit Cloud for full universe scans
- Memory usage spikes visible in Streamlit Cloud resource metrics near the 1GB limit

**Prevention:**
- Batch yfinance downloads: use `yfinance.download(tickers_list, ...)` with a single multi-ticker call rather than N individual `Ticker.history()` calls
- Set a hard cap of 50 tickers in the free-tier configuration; document the paid-tier path for larger universes
- Pre-compute and commit a daily snapshot via GitHub Actions so the Streamlit app only reads static files, never making live data calls during user sessions

---

## Shipping-Specific Pitfalls

### SS-1 Related-Party Transactions Distorting Reported Financials
**What goes wrong:** Many listed shipping companies are controlled by a family or private group that also owns the commercial management company, the technical manager, and sometimes the shipbroker. Management fees, charter rates paid to related parties, and vessel acquisition prices from related sellers can all be set at non-arm's-length terms. Reported EBITDA may be 20–40% lower than a stand-alone operator would achieve.

**Warning signs:**
- 20-F discloses "management fees paid to related parties" > 3% of gross revenue
- Company acquired vessels from a related party at prices above contemporaneous secondhand market
- Effective daily OPEX per vessel is > 30% higher than sector median without an obvious explanation

**Prevention:**
- Parse the "Related Party Transactions" note from 20-F for each company
- Flag companies where related-party fees > 2% of revenue as RELATED_PARTY_RISK
- Adjust EBITDA downward by disclosed management fees when computing normalized FCF; show this adjustment explicitly

---

### SS-2 Confusing Time Charter Equivalent with Spot Rate
**What goes wrong:** The spot rate (e.g. BDI for a given route) is a one-voyage market rate. The TCE rate is the net daily earnings after deducting voyage costs (bunker fuel, port costs, canal tolls) normalized to a per-day basis. For a slow-steaming Capesize on a trans-Pacific voyage, TCE can be 15–25% below the headline spot rate. Displaying the raw spot rate as the "earnings estimate" overstates realized revenue.

**Warning signs:**
- Earnings model implies TCE/day 20% above what management guidance shows for the same period
- Model-implied payout ratio exceeds 100% while actual dividend is sustainable

**Prevention:**
- Always label rate indices as "spot/voyage rate" and compute a separate TCE estimate using standard voyage cost deductions (bunker consumption model by vessel class, typical port costs)
- Provide a TCE-conversion factor per vessel class as a configurable parameter; default values from published broker reports
- In the dashboard, show "Est. TCE/day" not "Rate" to make the distinction explicit to users

---

### SS-3 Ignoring Sub-Sector Rate Drivers
**What goes wrong:** Each shipping sub-sector has different demand drivers. Dry bulk = Chinese steel/coal/grain imports. Crude tankers = OPEC production + refinery throughput. Product tankers = refinery dislocation (e.g. Russia sanctions moved product flows). LNG = Henry Hub vs TTF arbitrage. Container = consumer goods demand. A single "shipping rate" input produces nonsense composite scores when applied across sub-sectors.

**Prevention:** See MP-3 above. This is restated here as a domain-knowledge gap rather than a model architecture issue: the analyst building this tool must understand that shipping is five distinct businesses with uncorrelated rate cycles.

---

### SS-4 Orderbook and Fleet Supply Blindspot
**What goes wrong:** Rate forecasts based purely on historical rate time series miss the most important structural signal: the vessel orderbook. When newbuilding deliveries are 15%+ of the existing fleet scheduled over 2 years, rates are almost certain to fall regardless of demand. Ignoring the orderbook creates overconfident bull signals in oversupply windows.

**Warning signs:**
- Rate forecast is bullish during a period when the Clarksons orderbook-to-fleet ratio is > 12%
- Model failed to predict the container rate collapse of 2022–2023 (orderbook hit 30%+ of fleet)

**Prevention:**
- Source orderbook-to-fleet ratios from public data (Clarksons publishes summaries; UNCTAD annual shipping report is free; Lloyd's List Intelligence has free excerpts)
- Include orderbook/fleet as an exogenous feature in the XGBoost rate model
- Display a "fleet supply risk" indicator per sub-sector in the dashboard

---

### SS-5 Drydock Off-Hire and Utilization Assumptions
**What goes wrong:** A 98% utilization assumption is common in sell-side models but unrealistic. Realistic utilization for an actively trading fleet is 92–95% after accounting for drydocks, positioning voyages, idle time, and minor technical stoppages. Using 98% inflates revenue projections by 3–6%.

**Prevention:**
- Default utilization to 93% in FCF scenarios; allow configuration per company based on disclosed historical utilization
- Separately model drydock years (lower utilization ~88%) vs non-drydock years

---

## Phase Mapping

| Pitfall | Phase to Address |
|---------|-----------------|
| DP-1 Stale yfinance prices for European stocks | Phase 1: Data Ingestion — add staleness detection and STALE_PRICE flag |
| DP-2 BDI holiday gaps | Phase 1: Data Ingestion — holiday calendar + gap-fill policy |
| DP-3 Survivorship bias | Phase 1: Data Ingestion — static versioned universe.yaml with delisted tickers |
| DP-4 Currency mismatch | Phase 1: Data Ingestion — reporting_currency / trading_currency fields + FX conversion |
| DP-5 SEC 20-F parsing failures | Phase 2: Financial Parsing — balance-sheet identity validation on every 20-F parse |
| MP-1 Book NAV vs market NAV | Phase 3: NAV Engine — use secondhand vessel indices as primary; book value as fallback |
| MP-2 Charter coverage in FCF | Phase 3: NAV Engine / Phase 4: FCF Scenarios — parse fleet employment table |
| MP-3 Sub-sector conflation | Phase 2: Universe Setup — sub-sector tagging; Phase 4: Rate Forecast — per-sector models |
| MP-4 Rate forecast overfitting | Phase 4: Rate Forecast — 20-year training window; 2018–2019 held-out validation |
| MP-5 GAAP EPS vs TCE metrics | Phase 3 / Phase 5: Scoring — suppress EPS; surface TCE/day and EV/EBITDA |
| MP-6 Drydock in FCF | Phase 4: FCF Scenarios — drydock capex and off-hire model per fleet age |
| IP-1 App sleep / cache loss | Phase 6: Infrastructure — static committed data fallback; "data as of" timestamp |
| IP-2 Ephemeral filesystem | Phase 6: Infrastructure — GitHub Actions pre-compute; no runtime writes |
| IP-3 Secrets leaking | Phase 6: Infrastructure — .gitignore from commit 0; secrets audit |
| IP-4 Free-tier rate limits | Phase 6: Infrastructure — batched yfinance; 50-ticker cap; static snapshot path |
| SS-1 Related-party transactions | Phase 3: Financial Parsing — parse RPT note; RELATED_PARTY_RISK flag |
| SS-2 TCE vs spot rate confusion | Phase 4 + Phase 5: Scoring + Dashboard — label TCE explicitly; voyage cost deduction |
| SS-3 Sub-sector rate drivers | Phase 4: Rate Forecast — sub-sector-specific rate indices |
| SS-4 Orderbook blindspot | Phase 4: Rate Forecast — orderbook/fleet as exogenous regressor |
| SS-5 Drydock utilization | Phase 4: FCF Scenarios — 93% default; per-company configurability |
