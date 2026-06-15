# Shipping Stock Dashboard

## What This Is

A personal investment research dashboard deployed on Streamlit Community Cloud that tracks US and European listed shipping stocks across all sub-sectors (crude tankers, product tankers, dry bulk, LNG/LPG, containers). It combines a quantitative price model — built from NAV analysis, freight rate forecasting, FCF scenarios, and capital allocation scoring — to show at a glance whether each stock is cheap, fairly priced, or expensive relative to its fundamental value.

## Core Value

A composite buy/sell signal per stock, grounded in shipping-specific fundamentals (NAV discount, rate cycle position, FCF yield), that tells the user whether a stock is worth buying right now.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Dashboard shows all tracked shipping stocks with live intraday prices (15-60 min refresh via yfinance)
- [ ] Stocks grouped by sub-sector: crude tankers, product tankers, dry bulk, LNG/LPG, containers
- [ ] Daily data pipeline ingests BDI/BDTI/BCTI rates, macro features (iron ore, coal, oil, VIX, DXY) from free sources (FRED, Quandl, Yahoo Finance)
- [ ] NAV engine computes fleet asset value per company from 20-F fleet data + vessel age/type regression
- [ ] Rate forecast model (XGBoost + SARIMA ensemble) produces 3/6/12-month bear/base/bull scenarios
- [ ] FCF scenario engine: TCE rate × charter coverage × fleet size → annual FCF per scenario
- [ ] P/NAV regression identifies whether stock is trading at discount or premium vs fundamentals
- [ ] Composite score (0–100) per stock across: rate momentum, valuation, supply tightness, balance sheet, capital allocation
- [ ] Dashboard shows score, P/NAV ratio, FCF yield, and buy/hold/avoid signal per stock
- [ ] Deployed on Streamlit Community Cloud, accessible from any browser

### Out of Scope

- Authentication / multi-user access — personal tool only
- Paid data sources (Bloomberg, Clarksons, VesselsValue subscriptions) — free sources only for v1
- Real-time tick-by-tick price streaming — 15-60 min is sufficient for fundamental model
- Mobile app — browser dashboard is enough
- Trade execution / broker integration — research only
- Alerts / notifications — v2 if needed
- Backtesting engine — v2

## Context

- Shipping stocks are valued primarily by NAV (fleet asset value minus debt) and freight rate cycle position, not traditional DCF
- Baltic Exchange publishes BDI/BDTI/BCTI once per day — daily rate refresh is the natural cadence
- Academic foundation: Bakshi et al. (2012) for BDI→stock return link; Andrikopoulos et al. (2022) for P/NAV premium drivers; 2025 PMC paper for ML vessel valuation
- Mintzmyer (Value Investor's Edge) guides on Seeking Alpha cover the practitioner framework (NAV, TCE metrics, seasonality, capital allocation) — PDFs saved locally at ~/Desktop/shipping_guide/
- No open-source shipping NAV/equity model exists publicly — this is novel
- Target stock universe:
  - US-listed: ZIM, GOGL, DHT, STNG, INSW, TRMD, SFL, EGLE, SBLK, TNK, FRO, HAFNI, NMM, GLNG
  - European (Oslo/London): HAFNI.OL, ODF.OL, MPCC.OL, HLNG.OL, FRO.OL

## Constraints

- **Budget**: Free data sources only (FRED, Yahoo Finance, Quandl, UNCTAD, Bimco free reports)
- **Hosting**: Streamlit Community Cloud free tier (sleeps on inactivity, wakes in ~30s — acceptable for personal use)
- **Stack**: Python only — pandas, yfinance, scikit-learn/XGBoost, statsmodels, Streamlit
- **Data cadence**: Stock prices every 15-60 min via yfinance; rates + fundamentals once daily via scheduled pipeline
- **Fleet data**: Parsed from SEC 20-F annual filings (free, manual for v1; automated for v2)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Streamlit Community Cloud for hosting | Free, Python-native, no infra to manage, shareable URL | — Pending |
| yfinance for intraday stock prices | Free, no API key, covers all US + some European listings | — Pending |
| XGBoost + SARIMA ensemble for rate forecast | Literature shows XGBoost beats ARIMA on BDI; SARIMA captures proven seasonality | — Pending |
| Free data sources only in v1 | Validate model usefulness before paying for Clarksons/VesselsValue | — Pending |
| Personal use only, no auth | Reduces scope significantly; Streamlit public URL is acceptable | — Pending |

---
*Last updated: 2026-06-15 after initialization*
