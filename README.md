# Shipping Stock Dashboard

> A quantitative investment research dashboard for US and European listed shipping equities — combining freight rate forecasting, Net Asset Value (NAV) analysis, Free Cash Flow (FCF) scenario modelling, and capital allocation scoring into a unified buy/hold/avoid signal.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Shipping Equity Universe](#2-the-shipping-equity-universe)
3. [Why Standard Valuation Fails for Shipping](#3-why-standard-valuation-fails-for-shipping)
4. [The 4-Layer Pricing Model](#4-the-4-layer-pricing-model)
   - 4.1 [Layer 1: Freight Rate Forecasting](#41-layer-1-freight-rate-forecasting)
   - 4.2 [Layer 2: NAV Engine](#42-layer-2-nav-engine)
   - 4.3 [Layer 3: Equity Pricing Model](#43-layer-3-equity-pricing-model)
   - 4.4 [Layer 4: Composite Score](#44-layer-4-composite-score)
5. [Data Sources](#5-data-sources)
6. [System Architecture](#6-system-architecture)
7. [Dashboard Features](#7-dashboard-features)
8. [Academic Foundation](#8-academic-foundation)
9. [Deployment](#9-deployment)
10. [Roadmap](#10-roadmap)

---

## 1. Project Overview

Shipping stocks are among the most cyclical and misunderstood asset classes in public equity markets. Standard tools — P/E ratios, DCF models, EPS estimates — systematically misfail on shipping companies because earnings swing 10x between cycle trough and peak, while the real value driver is the market price of the physical fleet of vessels.

This project builds a **quantitative research dashboard** that applies the correct framework for shipping equity analysis:

- **Net Asset Value (NAV)** as the fundamental anchor — what would the fleet sell for today?
- **Freight rate forecasting** as the earnings engine — where are rates going in 3/6/12 months?
- **FCF scenario modelling** as the near-term return driver — how much cash does the company generate per scenario?
- **Composite scoring** as the actionable signal — is this stock cheap, fairly priced, or expensive right now?

The result is a Streamlit dashboard deployed on Streamlit Community Cloud, refreshing stock prices every 15-60 minutes and fundamentals daily, covering 20+ listed shipping companies across all major sub-sectors.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHIPPING STOCK DASHBOARD                      │
│                                                                   │
│  Sub-sector: Crude Tankers ▾                                     │
│                                                                   │
│  Ticker   Price   P/NAV   FCF Yield   Rate Mom.   Score  Signal │
│  ──────   ─────   ─────   ─────────   ─────────   ─────  ────── │
│  FRO      $18.2   0.81x     14.2%       ▲ +12%      74   BUY    │
│  DHT      $11.4   0.93x      9.8%       ▲  +8%      61   HOLD   │
│  TNK      $52.1   1.12x      6.1%       ─  +1%      44   HOLD   │
│  INSW     $43.7   1.34x      3.2%       ▼  -4%      28   AVOID  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. The Shipping Equity Universe

The dashboard covers **20+ listed shipping companies** across five sub-sectors, spanning US (NYSE/NASDAQ) and European (Oslo Børs, London) listings.

### 2.1 Coverage Universe

| Sub-Sector | Ticker | Exchange | Company | Vessels | DWT (approx) |
|---|---|---|---|---|---|
| **Crude Tankers** | FRO | NYSE | Frontline plc | ~70 VLCCs/Suezmaxes | ~14M |
| | DHT | NYSE | DHT Holdings | ~23 VLCCs | ~7M |
| | TNK | NYSE | Teekay Tankers | ~50 Suezmaxes/Aframaxes | ~6M |
| | INSW | NYSE | International Seaways | ~60 mixed tankers | ~8M |
| | FRO.OL | Oslo | Frontline (dual-listed) | — | — |
| **Product Tankers** | STNG | NYSE | Scorpio Tankers | ~100 MR/LR tankers | ~7M |
| | TRMD | NASDAQ | TORM plc | ~80 MR/LR tankers | ~5M |
| | HAFNI | NASDAQ | Hafnia Ltd | ~200 product tankers | ~12M |
| | HAFNI.OL | Oslo | Hafnia (dual-listed) | — | — |
| **Dry Bulk** | GOGL | NYSE | Golden Ocean | ~80 Capesizes/Panamaxes | ~12M |
| | SBLK | NASDAQ | Star Bulk Carriers | ~120 mixed bulkers | ~14M |
| | EGLE | NASDAQ | Eagle Bulk | ~50 Supramaxes | ~3M |
| **LNG / LPG** | GLNG | NYSE | Golar LNG | ~10 LNG carriers | — |
| | SFL | NYSE | SFL Corporation | ~80 diversified | — |
| | HLNG.OL | Oslo | Höegh LNG | ~10 FSRUs | — |
| **Container** | ZIM | NYSE | ZIM Integrated | ~150 containers | ~450K TEU |
| | MPCC.OL | Oslo | MPC Container Ships | ~60 feeder vessels | ~120K TEU |
| **Diversified** | NMM | NYSE | Navios Maritime Partners | ~190 mixed | — |

### 2.2 Sub-Sector Characteristics

Each sub-sector has different rate drivers, seasonality, and valuation dynamics:

| Sub-Sector | Key Rate Index | Peak Season | Primary Demand Driver | Typical Vessel Value Range |
|---|---|---|---|---|
| Crude Tankers | BDTI (Baltic Dirty Tanker Index) | Q4 (winter demand) | Crude oil import volumes, OPEC production | $60M–$130M (VLCC) |
| Product Tankers | BCTI (Baltic Clean Tanker Index) | Q1 + Q3 | Refinery runs, gasoline/jet fuel trade | $25M–$60M (MR) |
| Dry Bulk | BDI (Baltic Dry Index) | Q3–Q4 (grain/coal) | Iron ore, coal, grain seaborne trade | $15M–$55M (Capesize) |
| LNG | LNG spot rates | Winter (heating) | LNG contract buildout, spot arbitrage | $200M–$250M (LNGC) |
| Container | SCFI (Shanghai Containerized) | Pre-Chinese New Year | Consumer goods trade, inventory cycles | $20M–$200M (depends) |

---

## 3. Why Standard Valuation Fails for Shipping

### 3.1 The GAAP EPS Problem

Standard P/E analysis systematically misprices shipping stocks because GAAP earnings are dominated by non-cash depreciation charges that bear no relationship to actual cash generation.

**Example — Frontline (FRO) in a strong rate environment:**

| Metric | GAAP | Shipping-Correct |
|---|---|---|
| Revenue | $1.8B | $1.8B |
| Depreciation | -$420M | N/A (vessel values rising) |
| GAAP Net Income | $380M | — |
| P/E (GAAP) | 5.2x | N/A |
| TCE Revenue | — | $1.4B |
| Opex | — | -$380M |
| **Daily FCF/vessel** | — | **$28,400/day** |
| **Annual FCF/share** | — | **$4.80** |
| **P/FCF** | — | **4.1x** |

The TCE (Time Charter Equivalent) rate — net revenue per vessel per day after voyage costs — is the correct earnings metric. A VLCC earning $35,000/day with $8,500/day opex generates $26,500/day in operating cash flow. Multiply by fleet size and days, subtract interest and G&A, and you have the actual FCF.

### 3.2 The Cycle Problem

Shipping earnings are not mean-reverting around a stable level — they follow a commodity super-cycle driven by the supply/demand balance of the global fleet. The same company can earn:

```
Rate Scenario     TCE Rate/day    Annual FCF/share    P/FCF at $18 stock
──────────────    ────────────    ─────────────────   ──────────────────
Trough (2020)       $8,000            -$0.80              N/A (loss)
Base (2024)        $28,000            $3.20               5.6x
Peak (2022)        $65,000            $9.40               1.9x
```

A static P/E model applied at any point in this cycle will give a completely wrong answer. The correct approach is to know *where in the cycle* you are and what rates are likely to do next.

### 3.3 The NAV Anchor

The most reliable long-term anchor is **Net Asset Value** — what would the company be worth if you liquidated the fleet at today's secondhand market prices and paid off the debt?

```
NAV per share  =  (Fleet Market Value + Cash - Total Debt)  ÷  Shares Outstanding
```

Historically, shipping stocks trade between 0.5x NAV (deep trough, balance sheet stress) and 1.8x NAV (cycle peak, rate euphoria). Mean reversion to 1.0x NAV is the dominant force over 2-3 year horizons.

```
P/NAV Distribution (historical, dry bulk):

  Frequency
      │
   35%┤     ████
   30%┤   ████████
   25%┤  ██████████
   20%┤ ████████████
   15%┤████████████████
   10%┤██████████████████████
    5%┤████████████████████████████
      └─────────────────────────────────
      0.3x  0.6x  0.9x  1.2x  1.5x  1.8x
                         ↑
                      Today's mean
```

---

## 4. The 4-Layer Pricing Model

The model is structured as four sequential layers, where each layer feeds into the next:

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1: FREIGHT RATE FORECAST                                   │
│  BDI/BDTI/BCTI + macro features → XGBoost+SARIMA ensemble        │
│  Output: 3/6/12-month rate scenarios (bear/base/bull)            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 2: NAV ENGINE                                              │
│  Fleet list + vessel age/type → market value regression          │
│  Output: NAV per share, P/NAV ratio per company                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 3: EQUITY PRICING MODEL                                    │
│  Rate scenarios × fleet × charter coverage → FCF scenarios       │
│  P/NAV regression → target price range                           │
│  Cycle-phase blend → blended price target                        │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 4: COMPOSITE SCORE                                         │
│  5 dimensions → weighted 0-100 score → BUY / HOLD / AVOID        │
└──────────────────────────────────────────────────────────────────┘
```

---

### 4.1 Layer 1: Freight Rate Forecasting

#### 4.1.1 Input Features

| Feature | Source | Update Frequency | Rationale |
|---|---|---|---|
| BDI (Baltic Dry Index) | FRED / Baltic Exchange | Daily | Primary dry bulk rate benchmark |
| BDTI (Baltic Dirty Tanker Index) | FRED | Daily | Crude tanker benchmark |
| BCTI (Baltic Clean Tanker Index) | FRED | Daily | Product tanker benchmark |
| Iron ore price (62% Fe, CFR China) | Yahoo Finance (IRON) | Daily | Top BDI driver (SHAP evidence) |
| Thermal coal price | Yahoo Finance | Daily | Second BDI driver |
| Brent crude oil | Yahoo Finance (BZ=F) | Daily | Tanker demand proxy |
| VIX (CBOE Volatility Index) | Yahoo Finance (^VIX) | Daily | Global risk sentiment |
| DXY (USD Index) | Yahoo Finance (DX-Y.NYB) | Daily | Commodity/trade denominator |
| Seaborne trade volume index | UNCTAD (quarterly proxy) | Quarterly | Ton-mile demand |
| Orderbook-to-fleet ratio | Bimco (monthly) | Monthly | 12-24 month supply outlook |

#### 4.1.2 Model Architecture

The rate forecast uses a **stacked ensemble** of two complementary models:

**Model A — SARIMA (Seasonal ARIMA):**
Captures the well-documented seasonality in freight rates (Kavussanos & Alizadeh, 2002). Fitted separately per sub-sector index.

```
BDI_t = SARIMA(p, d, q)(P, D, Q, s=52)  [weekly seasonality]

Seasonal peaks historically observed:
  Dry Bulk:       Q3-Q4 (grain/coal harvest + pre-winter)
  Crude Tankers:  Q4    (winter heating demand)
  Product Tankers:Q1+Q3 (refinery maintenance seasons)
  LNG:            Q4-Q1 (winter heating)
```

**Model B — XGBoost Regressor:**
Captures non-linear relationships between macro features and rate changes. Feature importance (from 2025 PMC SHAP analysis):

```
Feature Importance (SHAP values, BDI model):

Iron ore price          ████████████████████  0.42
Coal price              ████████████          0.28
BDI lag (t-1)          ████████              0.19
DXY                    █████                 0.11
VIX                    ███                   0.07
Orderbook ratio        ██                    0.05
Oil price              ██                    0.04
```

**Ensemble:**
```
Rate_forecast = 0.4 × SARIMA_forecast + 0.6 × XGBoost_forecast

Weight calibration: cross-validated on 2015-2023 data
XGBoost weight higher: captures macro regime shifts better
SARIMA weight non-zero: ensures seasonality is preserved
```

#### 4.1.3 Output Scenarios

Three scenarios generated for each 3/6/12-month horizon:

| Scenario | Percentile | Construction |
|---|---|---|
| Bull | 75th | Ensemble forecast + 1σ confidence interval |
| Base | 50th | Ensemble point forecast |
| Bear | 25th | Ensemble forecast - 1σ confidence interval |

---

### 4.2 Layer 2: NAV Engine

#### 4.2.1 Fleet Data

For each company, the fleet list is parsed from SEC 20-F annual filings (for US-listed) and equivalent annual reports (for European-listed). Key data extracted per vessel:

| Field | Example | Source |
|---|---|---|
| Vessel name | Front Altair | 20-F fleet schedule |
| Vessel type | VLCC | 20-F |
| Deadweight tonnage (DWT) | 299,999 | 20-F |
| Year built | 2019 | 20-F |
| Age (years) | 6 | Computed |
| Charter type | Spot / TC | 20-F |
| Charter rate (if TC) | $42,000/day | 20-F |
| Charter expiry | 2026-Q2 | 20-F |

#### 4.2.2 Vessel Market Value Regression

Each vessel's current secondhand market value is estimated using an ML model trained on 8,948 reported secondhand sales (2008-2020, from Clarksons Research — basis for the 2025 PMC paper):

```
Vessel_MV = XGBoost(
    age,                    # non-linear: steep drop 0-5yr, gradual 5-20yr
    DWT,                    # larger vessels = higher absolute but lower $/DWT
    vessel_type_encoded,    # VLCC vs Suezmax vs Aframax etc.
    current_TCE_rate,       # rate environment at time of valuation
    engine_type_encoded,    # Eco/scrubber-fitted commands premium
    build_country_encoded,  # Korean/Japanese > Chinese yard premium
)

R² on validation set: ~0.89 (from literature)
```

**Vessel type depreciation profiles (approximate):**

```
Market Value as % of Newbuild Price:

Age:    0yr   5yr   10yr  15yr  20yr  25yr
VLCC:  100%   78%   59%   43%   28%   12%
MR:    100%   75%   55%   38%   22%    8%
Capesz:100%   72%   52%   35%   20%    6%
```

#### 4.2.3 NAV Calculation

```
For each company:

  Fleet Market Value  = Σ Vessel_MV(i)  for i in fleet
  Charter Premium     = Σ NPV(TC_rate - spot_rate) × remaining_days  [if TC > spot]
  Charter Discount    = Σ NPV(spot_rate - TC_rate) × remaining_days  [if TC < spot]

  Gross Asset Value   = Fleet Market Value ± Charter Adjustments + Cash & Equivalents

  Net Debt            = Total Debt - Cash
  Drydock Liability   = Σ estimated_drydock_cost(i) × P(drydock within 12m)

  NAV                 = Gross Asset Value - Net Debt - Drydock Liability
  NAV per share       = NAV ÷ Diluted Shares Outstanding
  P/NAV               = Current Stock Price ÷ NAV per share
```

**Historical P/NAV ranges by sub-sector:**

| Sub-Sector | Trough P/NAV | Mean P/NAV | Peak P/NAV | Current Signal |
|---|---|---|---|---|
| Crude Tankers | 0.45x | 0.92x | 1.75x | TBD (live) |
| Product Tankers | 0.50x | 0.95x | 1.80x | TBD (live) |
| Dry Bulk | 0.40x | 0.88x | 1.70x | TBD (live) |
| LNG | 0.70x | 1.10x | 1.60x | TBD (live) |
| Container | 0.35x | 0.80x | 2.50x | TBD (live) |

---

### 4.3 Layer 3: Equity Pricing Model

Two parallel approaches are computed and blended by cycle phase.

#### 4.3.1 Approach A — FCF Scenario Pricing

```
For each rate scenario (bear / base / bull):

  Spot_TCE        = forecasted_rate × (1 - voyage_cost_factor)
  TC_TCE          = weighted_average_contracted_rate  [from charter schedule]

  Daily_FCF       = (spot_pct × Spot_TCE + tc_pct × TC_TCE
                    - Opex_per_day
                    - G&A_per_vessel_per_day
                    - Interest_per_vessel_per_day)
                  × fleet_vessels
                  × (365 × (1 - drydock_pct))

  Annual_FCF      = Daily_FCF × 365
  FCF_per_share   = Annual_FCF ÷ Diluted_Shares

  Price_target_A  = FCF_per_share × P_FCF_multiple

P/FCF multiple calibration (from historical data):
  Rate upswing:   5–8x   (growth premium, dividend speculation)
  Rate plateau:   4–6x   (steady cash return)
  Rate downturn:  2–4x   (survival discount)
  Trough:         N/A    (losses; use NAV floor instead)
```

**Sample FCF output table (illustrative, Frontline):**

| Scenario | TCE Rate | FCF/Share | P/FCF | Price Target |
|---|---|---|---|---|
| Bull (75th pct) | $42,000/day | $6.80 | 6.5x | $44.20 |
| Base (50th pct) | $28,000/day | $3.90 | 5.5x | $21.45 |
| Bear (25th pct) | $14,000/day | $0.80 | 3.5x | $2.80 |

#### 4.3.2 Approach B — P/NAV Regression

Based on Andrikopoulos, Merika & Sigalas (2022), the following panel regression explains why some shipping stocks trade at NAV premiums or discounts:

```
P/NAV_it = β₀
         + β₁ × Leverage_it          (Net Debt / Fleet Value — higher = more discount)
         + β₂ × Bid_Ask_Spread_it    (illiquidity discount)
         + β₃ × Governance_Score_it  (related-party flags, board independence)
         + β₄ × Inst_Ownership_it    (institutional % — premium)
         + β₅ × Dividend_Yield_it    (cash return — premium)
         + β₆ × Acq_Premium_it       (fleet acquired above/below market)
         + α_i                        (company fixed effects)
         + ε_it

R² ≈ 0.61 (from literature on similar panel)
```

The regression is re-estimated quarterly as new 20-F data becomes available, and used to predict each company's "fair" P/NAV multiple.

```
Price_target_B  = NAV_per_share × predicted_fair_P/NAV
```

#### 4.3.3 Cycle-Phase Blending

```
Cycle phase detection:
  - Rate momentum (3M change in sector index) > +15%  → "upswing"
  - Rate momentum between -15% and +15%               → "plateau"
  - Rate momentum < -15%                              → "downturn"
  - P/NAV < 0.6x AND rate momentum < 0%              → "trough"

Blended price target:
  Upswing:   0.70 × Price_target_A (FCF)  +  0.30 × Price_target_B (NAV)
  Plateau:   0.50 × Price_target_A        +  0.50 × Price_target_B
  Downturn:  0.30 × Price_target_A        +  0.70 × Price_target_B
  Trough:    NAV per share × 0.75  (balance sheet survival floor)
```

---

### 4.4 Layer 4: Composite Score

Each stock receives a **composite score from 0 to 100**, computed across five dimensions. The signal thresholds are calibrated to historical return distributions.

#### 4.4.1 Dimension Scoring

| Dimension | Weight | Score Input | Scoring Logic |
|---|---|---|---|
| Rate Momentum | 25% | 3M change in sector rate index | +20pts per σ above mean; −20pts per σ below |
| Valuation | 25% | P/NAV percentile (vs 5-year history) | 100 − (percentile × 100); cheaper = higher score |
| Supply Tightness | 20% | Orderbook/fleet %; avg fleet age | Low orderbook + old fleet = high score |
| Balance Sheet | 15% | Net LTV; months of liquidity at base FCF | Low leverage + long runway = high score |
| Capital Allocation | 15% | Buyback yield + dividend yield + governance | Higher return + clean governance = higher score |

#### 4.4.2 Signal Thresholds

```
Score Range    Signal    Interpretation
───────────    ──────    ──────────────────────────────────────────────────
  75 – 100     BUY       Strong fundamental case; rate tailwind + NAV discount
  50 –  74     HOLD      Fair value or mixed signals; monitor for catalyst
  25 –  49     AVOID     Overvalued vs NAV or rate headwinds developing
   0 –  24     SELL      Significant premium to NAV + deteriorating rates

Colour coding in dashboard:
  BUY   → green  (#22c55e)
  HOLD  → yellow (#eab308)
  AVOID → orange (#f97316)
  SELL  → red    (#ef4444)
```

#### 4.4.3 Score Breakdown Display

For each stock, the dashboard shows the score breakdown so the signal is never a black box:

```
FRO — Frontline plc            SCORE: 74 / 100  ●  HOLD
─────────────────────────────────────────────────────────
  Rate Momentum     ████████████████░░░░  18/25  ▲ BDTI +11% (3M)
  Valuation         ████████████████████  20/25  P/NAV 0.81x (23rd pct)
  Supply Tightness  ████████████░░░░░░░░  12/20  Orderbook 7.2%, avg age 10yr
  Balance Sheet     ████████░░░░░░░░░░░░   8/15  LTV 58%, 14mo liquidity
  Capital Alloc.    ████████████░░░░░░░░  12/15  9.4% div yield, low RPT flags
─────────────────────────────────────────────────────────
  NAV/share: $22.50   P/NAV: 0.81x   FCF/share (base): $3.90
  Price targets:  Bear $8.20  |  Base $21.45  |  Bull $44.20
  Data as of: 2026-06-15 14:32 UTC
```

---

## 5. Data Sources

All data sources used in v1 are **free and publicly accessible**.

| Data Type | Source | Access Method | Refresh | Notes |
|---|---|---|---|---|
| Stock prices (US-listed) | Yahoo Finance | `yfinance` Python library | 15-60 min | Covers all NYSE/NASDAQ |
| Stock prices (European) | Yahoo Finance | `yfinance` (suffix .OL, .L) | 15-60 min | Oslo + London via Yahoo |
| BDI (Baltic Dry Index) | FRED | `fredapi` (series BDIYINDEX) | Daily | Free, no API key needed |
| BDTI (Baltic Dirty Tanker) | FRED | `fredapi` (series BDIYINDEX) | Daily | Published by Baltic Exchange |
| BCTI (Baltic Clean Tanker) | Yahoo Finance | `yfinance` (^BCTI proxy) | Daily | |
| Iron ore price | Yahoo Finance | `yfinance` (IRON=F or proxy) | Daily | SGX TSI Iron Ore CFR China |
| Thermal coal price | Yahoo Finance | `yfinance` | Daily | |
| Brent crude oil | Yahoo Finance | `yfinance` (BZ=F) | Daily | |
| VIX | Yahoo Finance | `yfinance` (^VIX) | Daily | |
| DXY (USD Index) | Yahoo Finance | `yfinance` (DX-Y.NYB) | Daily | |
| Orderbook-to-fleet ratio | Bimco | Web scrape / manual | Monthly | Free reports published monthly |
| Fleet data (vessel list) | SEC EDGAR | 20-F filing parser | Quarterly | Annual, updated on filing |
| Macro economic data | FRED | `fredapi` | Daily | GDP, trade volumes, industrial production |
| Ton-mile demand proxy | UNCTAD | Manual download | Quarterly | Free annual reports |

### 5.1 Rate Index Reference

| Index | Measures | Where to Find | Ticker |
|---|---|---|---|
| BDI | Dry bulk composite (4 vessel sizes) | FRED: BDIYINDEX | — |
| BCI | Capesize rates (180K DWT) | Baltic Exchange | — |
| BPI | Panamax rates (75K DWT) | Baltic Exchange | — |
| BSI | Supramax rates (55K DWT) | Baltic Exchange | — |
| BHSI | Handysize rates (35K DWT) | Baltic Exchange | — |
| BDTI | Dirty tanker composite | FRED | — |
| BCTI | Clean tanker composite | Baltic Exchange | — |
| SCFI | Shanghai containerized freight | Freightos / Yahoo proxy | — |

---

## 6. System Architecture

### 6.1 Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│  DATA INGESTION LAYER                                            │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│  │  yfinance  │  │  FRED API  │  │  SEC EDGAR │                 │
│  │  (prices)  │  │  (rates)   │  │  (fleet)   │                 │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                 │
│        └───────────────┴───────────────┘                        │
│                         │                                        │
│                   ┌─────▼──────┐                                 │
│                   │  Parquet   │  (persisted daily snapshots)    │
│                   │  Store     │                                 │
│                   └─────┬──────┘                                 │
└─────────────────────────┼───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  MODEL LAYER                                                     │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Rate        │  │ NAV         │  │ FCF Scenario            │  │
│  │ Forecast    │→ │ Engine      │→ │ Engine                  │  │
│  │ SARIMA+XGB  │  │ Fleet MV    │  │ Rate × Fleet × Coverage │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│         └──────────────────────────────────┘                    │
│                              │                                   │
│                   ┌──────────▼──────────┐                        │
│                   │  Composite Scorer   │                        │
│                   │  (5 dimensions)     │                        │
│                   └──────────┬──────────┘                        │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  STREAMLIT DASHBOARD                                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Overview     │  │ Stock Detail │  │ Rate Monitor         │   │
│  │ Screener     │  │ (per ticker) │  │ (BDI/BDTI/BCTI)      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Refresh Architecture

```
Intraday refresh (every 30 min):
  GitHub Actions scheduled workflow
  → yfinance.download(tickers, period="1d", interval="30m")
  → Write to data/prices/YYYY-MM-DD.parquet
  → Commit to repo (triggers Streamlit Cloud redeploy? No — uses st.cache_data TTL)

Daily refresh (6:00 UTC, after Baltic Exchange publishes):
  GitHub Actions scheduled workflow
  → Fetch FRED rates, Yahoo macro features
  → Run rate forecast model
  → Recompute NAV (if new 20-F filed) or use cached fleet data
  → Recompute FCF scenarios + composite scores
  → Write to data/fundamentals/YYYY-MM-DD.parquet
  → Commit to repo

Streamlit App:
  → st.cache_data(ttl=1800) for price data   [30-min TTL]
  → st.cache_data(ttl=86400) for model data  [24-hr TTL]
  → Reads parquet files from repo on each cache miss
```

### 6.3 Repository Structure

```
shipping-stock-dashboard/
├── app/
│   ├── main.py              # Streamlit entry point
│   ├── pages/
│   │   ├── 01_Overview.py   # Screener table (all stocks)
│   │   ├── 02_Stock.py      # Individual stock deep-dive
│   │   └── 03_Rates.py      # Rate monitor + forecast charts
│   └── components/
│       ├── score_card.py    # Score breakdown widget
│       └── nav_chart.py     # P/NAV history chart
├── src/
│   ├── ingestion/
│   │   ├── prices.py        # yfinance wrapper
│   │   ├── rates.py         # FRED + macro data
│   │   └── fleet.py         # SEC 20-F parser
│   ├── models/
│   │   ├── rate_forecast.py # SARIMA + XGBoost ensemble
│   │   ├── nav_engine.py    # Vessel valuation + NAV
│   │   ├── fcf_engine.py    # FCF scenario builder
│   │   └── scorer.py        # Composite score calculator
│   └── config/
│       ├── universe.py      # Stock universe definition
│       └── settings.py      # pydantic-settings config
├── data/
│   ├── prices/              # Parquet: daily price snapshots
│   ├── rates/               # Parquet: BDI/BDTI/BCTI history
│   ├── fundamentals/        # Parquet: scored output per stock
│   └── fleet/               # JSON: fleet lists per company
├── .github/
│   └── workflows/
│       ├── refresh_prices.yml    # Every 30 min
│       └── refresh_daily.yml     # Daily at 6:00 UTC
├── tests/
├── .planning/               # GSD planning documents
├── requirements.txt
└── README.md
```

---

## 7. Dashboard Features

### 7.1 Overview Screener

The main page shows all tracked stocks in a sortable table:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  SHIPPING STOCK DASHBOARD          Last updated: 2026-06-15 14:32 UTC  [↻ Refresh]│
│                                                                                    │
│  Filter: [All Sectors ▾]  [All Exchanges ▾]  [Score: 0-100 ──●──────]             │
│                                                                                    │
│  Ticker  Company              Sector    Price  Chg%   P/NAV  FCF Yld  Score  Sig  │
│  ──────  ───────────────────  ────────  ─────  ────   ─────  ───────  ─────  ───  │
│  FRO     Frontline plc        Crude     $18.2  +1.2%  0.81x   14.2%    74   HOLD  │
│  GOGL    Golden Ocean         Dry Bulk  $12.8  -0.4%  0.74x   18.6%    81   BUY   │
│  STNG    Scorpio Tankers      Product   $52.1  +2.1%  0.92x   11.3%    67   HOLD  │
│  SBLK    Star Bulk            Dry Bulk   $9.4  +0.8%  0.68x   21.4%    85   BUY   │
│  ZIM     ZIM Integrated       Container $14.6  -3.2%  1.21x    2.1%    29   AVOID │
│  ...                                                                               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Stock Deep-Dive Page

Clicking any stock opens a detailed view with:
- Price chart with NAV overlay (shows P/NAV history)
- FCF scenario waterfall (bear/base/bull)
- Score breakdown bar chart
- Fleet summary table
- Charter coverage timeline
- Rate exposure analysis

### 7.3 Rate Monitor Page

- Live BDI / BDTI / BCTI chart (trailing 2 years)
- 12-month rate forecast with confidence bands
- Orderbook-to-fleet ratio chart
- Seasonal pattern overlay

---

## 8. Academic Foundation

This model is grounded in peer-reviewed shipping finance literature:

| Paper | Key Finding | Applied In |
|---|---|---|
| Bakshi, Panayotov & Skoulakis (2012, JFE) | BDI growth rate predicts global equity returns and economic activity weeks ahead | Layer 1: BDI used as leading indicator in rate forecast |
| Andrikopoulos, Merika & Sigalas (2022, European Financial Management) | P/NAV deviations explained by leverage, governance, liquidity, dividend policy | Layer 3: P/NAV regression specification |
| Kavussanos & Alizadeh (2002, Economic Modelling) | Statistically significant seasonality in tanker and dry bulk rates | Layer 1: SARIMA seasonal specification |
| PMC / PLoS ONE (2025) | XGBoost outperforms regression + RF on secondhand vessel price prediction; age, size, TCE rate are top features | Layer 2: Vessel MV regression |
| PMC BDI ML + SHAP (2025) | Iron ore and coal are top BDI drivers by SHAP attribution | Layer 1: XGBoost feature selection |
| Papailias & Thomakos (SSRN) | BDI exhibits mean-reverting cycles; GARCH family captures volatility clustering | Layer 1: confidence interval construction |

### 8.1 Practitioner Framework

The practitioner framework draws on J. Mintzmyer's *Shipping Investor Series* (Value Investor's Edge, Seeking Alpha):

| Guide | Applied Concept |
|---|---|
| Cash Flow Metrics | TCE, opex, daily FCF calculation methodology |
| The Importance of NAV | Fleet liquidation value as equity anchor |
| Asset & Charter Valuations | Charter premium/discount adjustment to vessel value |
| Financial & Operating Leverage | Spot vs TC exposure blending in FCF model |
| Demand Side Evaluation | Ton-mile demand as rate forecast input |
| Supply Side Evaluation | Orderbook/fleet ratio, scrapping curves |
| Seasonality Guides (6 sub-sectors) | SARIMA seasonal structure per sub-sector |
| Corporate Governance | Governance score in capital allocation dimension |

---

## 9. Deployment

### 9.1 Streamlit Community Cloud

```bash
# 1. Fork or clone this repo to your GitHub account
git clone https://github.com/Babbloo-studio/shipping-stock-dashboard
cd shipping-stock-dashboard

# 2. Create virtual environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Run locally
streamlit run app/main.py

# 4. Deploy to Streamlit Community Cloud
# → Go to share.streamlit.io
# → Connect GitHub repo
# → Set main file: app/main.py
# → Add secrets (FRED_API_KEY if using fredapi)
# → Deploy
```

### 9.2 GitHub Actions Schedules

```yaml
# .github/workflows/refresh_prices.yml
on:
  schedule:
    - cron: '*/30 9-22 * * 1-5'  # Every 30min, 9am-10pm UTC, weekdays only
```

```yaml
# .github/workflows/refresh_daily.yml
on:
  schedule:
    - cron: '0 6 * * 1-5'        # Daily at 6:00 UTC (after Baltic Exchange publishes)
```

### 9.3 Requirements

```
streamlit>=1.35.0
yfinance>=0.2.40
pandas>=2.2.0
numpy>=1.26.0
scikit-learn>=1.5.0
xgboost>=2.0.0
statsmodels>=0.14.0
fredapi>=0.5.1
plotly>=5.22.0
pydantic-settings>=2.3.0
pyarrow>=16.0.0
requests>=2.32.0
```

---

## 10. Roadmap

| Phase | Goal | Key Deliverables |
|---|---|---|
| 1 | Data pipeline | Price + rate ingestion, daily GitHub Actions refresh, parquet storage |
| 2 | NAV engine | Fleet parser, vessel MV regression, NAV per share per company |
| 3 | Rate forecast model | SARIMA + XGBoost ensemble, 3/6/12-month scenarios |
| 4 | FCF scenario engine | Charter coverage parser, daily FCF × rate scenario |
| 5 | Composite scorer | 5-dimension scoring, P/NAV regression, signal thresholds |
| 6 | Streamlit dashboard | Overview screener, stock deep-dive, rate monitor |
| 7 | Streamlit Cloud deployment | GitHub Actions pipelines, secrets, production deploy |

---

*Built on the quantitative framework from Value Investor's Edge (J. Mintzmyer) combined with academic shipping finance literature. No financial advice — for research purposes only.*
