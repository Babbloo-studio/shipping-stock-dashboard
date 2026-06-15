# Features Research: Shipping Stock Dashboard

## Table Stakes

These are the minimum features for the dashboard to be useful. Without them, a user would abandon it for a Bloomberg terminal or a spreadsheet.

### Stock Universe & Data

- **Ticker list with sub-sector tags** — crude tanker, product tanker, dry bulk, LNG/LPG, container. Every Finviz-style screener does this; without it you can't filter.
- **Current price + daily change** — trivially available via yfinance or a free market data API. Absence makes the dashboard dead on arrival.
- **Market cap + enterprise value** — essential for NAV and EV/EBITDA comparisons. Koyfin and Simply Wall St surface this in the first column.
- **52-week high/low + distance from high** — shipping stocks are cyclical; distance-from-high is a first-pass momentum signal every screener shows.
- **Volume and average volume** — needed to detect unusual activity; Finviz shows this prominently because illiquid shipping stocks can have sudden spikes.
- **Dividend yield (trailing and forward)** — many shipping stocks (STNG, DHT, EURN, HAFNIA) pay variable dividends tied to earnings; omitting yield would frustrate any income-focused research.

### Valuation Columns

- **P/E (trailing and forward)** — minimum credibility bar; every screener from Finviz to Koyfin shows this even for shipping where it is often meaningless at cycle troughs.
- **EV/EBITDA** — the standard shipping valuation multiple because it is capital-structure neutral and comparable across leverage levels.
- **P/NAV or P/Book** — the sector-specific metric. Breakwave's public commentary and Value Investor's Edge both anchor shipping analysis to NAV or book value. Without P/NAV the dashboard has no edge over Google Finance.
- **Price-to-FCF** — critical for variable dividend payers; ship owners return capital via buybacks + dividends tied to FCF. Seeking Alpha premium dashboards always include this for shipping.

### Rate and Freight Data

- **Spot rate display per sub-sector** — TD3C (VLCC), TC2/TC14 (product tanker), BDI/C5TC (capesize), Baltic Supramax, BLNG (LNG), SCFI/WCI (containers). This is the core fundamental input for all sub-sectors. Tools like Breakwave publish these; without live or recent rates the dashboard is disconnected from the actual business drivers.
- **Rate vs. prior week / prior month change** — shipping cycles move fast; a direction indicator is more actionable than a raw number.

### Composite Score Display

- **A visible buy/sell score or rating column** — even if it is derived from the NAV engine and FCF model, users need a synthesized output. Simply Wall St's snowflake score, Value Investor's Edge tier ratings, and Koyfin's factor scores all demonstrate that screener users want a number they can sort by, not just raw inputs.

---

## Differentiators

These features are what makes this dashboard worth building over just using Finviz.

### NAV Engine

- **Per-vessel-class NAV calculation** — fleet count × vessel class NAV benchmark (from VesselsValue public estimates or Clarkson proxies) minus net debt, divided by shares. This is the core moat. No generic screener does this. Value Investor's Edge subscribers pay for exactly this. Display as P/NAV with a traffic-light (below 0.8 = undervalued, above 1.2 = overvalued for the cycle).
- **NAV sensitivity slider** — let the user drag vessel prices ±20% and see how P/NAV changes. Ship values fluctuate with secondhand market; this interactive stress-test is not available in any public tool.
- **Historical P/NAV chart** — show where current P/NAV sits relative to the last 5-year range. This contextualizes the score far better than a point-in-time number.

### Rate Forecast Integration

- **Forward rate scenario selector** — bull / base / bear rate assumptions per sub-sector, used to calculate forward EBITDA. No screener does this; it is what a sell-side shipping analyst does in Excel. The dashboard makes it interactive.
- **Rate-to-earnings sensitivity table** — how much does EPS change if TC2 rates move $5,000/day? This is actionable for position sizing and is absent from all public screeners.
- **Rate cycle positioning indicator** — a simple heuristic (e.g., rates vs. 2-year average) that flags whether the sub-sector is in early upcycle, peak, or downcycle. Breakwave's ETF commentary does something similar in text form; this makes it visual and systematic.

### FCF Scenario Engine

- **Per-company FCF waterfall** — revenue from fleet × blended rate assumption, minus opex / G&A / drydocking reserve / interest, minus capex, equals FCF. Displayed as FCF yield and annualized dividend capacity. Seeking Alpha's VIE coverage does this in article form for individual names; doing it systematically across the universe is the differentiator.
- **Breakeven rate display** — the daily TCE rate at which the company covers cash costs and debt service. This is the single most useful number for risk management in shipping stocks and is not available in any screener. Operators publish it in earnings slides; extracting and displaying it creates a genuine edge.
- **FCF scenario toggle** — switch between bull/base/bear rate assumptions and see FCF yield update in real time.

### Composite Score

- **Multi-factor score with visible weights** — combine P/NAV discount, FCF yield, momentum (52-week price vs. peers), rate cycle position, and balance sheet strength (net debt / EBITDA) into a single 0–100 score. Show the sub-scores so the user can audit it. Unlike Simply Wall St's opaque snowflake, transparency here is the differentiator for a quant-oriented personal tool.
- **Score history sparkline** — a 90-day sparkline of the composite score per ticker so you can see if conviction is rising or falling, not just the current state.

### Cross-Sector Comparison

- **Sub-sector rotation view** — aggregate score by sub-sector (average P/NAV, FCF yield, rate momentum) in one row per sector. Helps decide where to rotate within shipping rather than stock-picking in isolation. No public tool does this at the sub-sector level with fundamental inputs.
- **Peer relative ranking within sub-sector** — rank each stock against its direct peers. Knowing that EURN is cheap vs. INSW on P/NAV within product tankers is more actionable than an absolute P/NAV number.

---

## Anti-Features

These features are tempting to build but consistently waste time in personal investment tools.

- **News feed / sentiment analysis** — shipping news sources (TradeWinds, Splash247) are not API-accessible for free. NLP sentiment on press releases is noisy and distracts from the rate/NAV fundamentals. Koyfin has this; it is mostly ignored by quant-focused users.
- **Technical analysis overlays (RSI, MACD, Bollinger)** — shipping stocks are fundamental/event-driven. Technical overlays add maintenance burden and chart clutter. Finviz has this; it is not what makes Finviz useful for shipping research.
- **Automated email / push alerts** — for personal use, the latency of checking the dashboard manually is acceptable. Building alert infrastructure (Twilio, email) is engineering overhead that does not improve the quality of the analysis.
- **User accounts / multi-user support** — personal use only. Adding auth (Streamlit authenticator, OAuth) adds complexity with zero research benefit.
- **Broker integration / portfolio tracking** — P&L tracking and position management belong in a brokerage app. Adding portfolio columns to the dashboard muddies its purpose (screening + research) with execution concerns.
- **Earnings call transcript summarization** — LLM summaries of transcripts sound useful but require API cost per call and produce generic outputs. Better to link to the Seeking Alpha transcript directly.
- **ESG scores** — shipping ESG data (CII ratings, carbon intensity) is not relevant to a price model focused on NAV and FCF. Including it would add data sourcing complexity with no analytical payoff for a 1–2 year investment horizon.
- **Order book / newbuild pipeline charts** — important for multi-year cycle analysis but complex to source (Clarkson data is paywalled) and updated infrequently. Reference in the rate forecast assumptions as a text note rather than building a data pipeline for it.

---

## Feature Complexity Notes

These features are harder to implement than they appear:

- **NAV engine** — requires sourcing secondhand vessel values. VesselsValue charges for API access. Free proxies: Clarkson's published benchmarks (quarterly PDF), Baltic Exchange press releases, broker research PDFs. The real challenge is keeping vessel counts current; companies update fleet composition in quarterly filings. Plan 4–6 hours per company to establish baseline fleet data, then quarterly maintenance.
- **Breakeven rate** — disclosed inconsistently across companies. Some report daily opex only; others include G&A allocation; few include drydocking reserves. Normalizing these requires reading each company's most recent earnings slide deck and making judgment calls. Treat it as a semi-manual field updated quarterly.
- **Rate data pipeline** — Baltic Exchange and Platts data requires subscriptions. Free workarounds: Breakwave's public ETF fact sheets (BDRY, BWET) publish index levels weekly; some brokers post weekly rate reports as public PDFs; Xeneta has a free tier for container rates. Scraping is fragile. Build a manual data-entry fallback so rates can be typed in when scrapers break.
- **FCF waterfall accuracy** — requires fleet-level daily opex, which varies by vessel age and management structure. For in-house managed fleets (Frontline, DHT) opex is stated in filings. For third-party managed (some smaller names) it is less transparent. Use the stated opex as the base and flag managed vs. in-house in the UI.
- **Composite score calibration** — the weights (P/NAV vs. FCF yield vs. momentum) are arbitrary until back-tested. For personal use, start with equal weights and adjust manually based on which signals predicted price moves in hindsight. Building a formal backtester is a separate project.
- **Streamlit performance with live data** — fetching prices, computing NAV, and rendering charts for 20–30 tickers on every page load will be slow. Cache aggressively with `@st.cache_data(ttl=3600)`. Separate the static (fleet, opex) from the dynamic (price, rates) data refresh cycles.

---

## Dependencies Between Features

Build in this order; each layer depends on the previous:

1. **Stock universe + sub-sector tags** — the foundation everything else filters by.
2. **Price + market data fetch** (yfinance or similar) — needed before any valuation column works.
3. **Static fundamental data store** (fleet counts, opex, debt) — manual or semi-manual, updated quarterly. NAV engine and FCF model both consume this.
4. **Rate data ingestion** — spot rates per sub-sector. Can be manual entry initially; automate later.
5. **NAV engine** — depends on vessel price benchmarks (static, updated monthly) + fleet data (step 3).
6. **FCF scenario engine** — depends on rate data (step 4) + static fundamental data (step 3).
7. **Composite score** — depends on NAV (step 5) + FCF (step 6) + price data (step 2).
8. **Rate forecast / scenario toggles** — depends on rate ingestion (step 4) and FCF engine (step 6); adds interactivity on top of working calculations.
9. **Peer relative ranking and sub-sector rotation view** — depends on composite score (step 7) being computed for all tickers.
10. **Historical P/NAV chart + score sparklines** — depends on all of the above being stored over time; requires a lightweight time-series store (SQLite or Parquet files in the repo).

The critical path is steps 1–7. Steps 8–10 are enhancements once the core model is working.
