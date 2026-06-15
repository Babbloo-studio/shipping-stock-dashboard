from dataclasses import dataclass, field


@dataclass
class Stock:
    ticker: str
    name: str
    sector: str
    exchange: str
    currency: str = "USD"
    # approximate fleet opex per vessel per day (USD)
    opex_per_day: int = 8500
    # typical G&A allocated per vessel per day
    gna_per_day: int = 800


UNIVERSE: list[Stock] = [
    # Crude Tankers
    Stock("FRO", "Frontline plc", "Crude Tanker", "NYSE", opex_per_day=9200),
    Stock("DHT", "DHT Holdings", "Crude Tanker", "NYSE", opex_per_day=8800),
    Stock("TNK", "Teekay Tankers", "Crude Tanker", "NYSE", opex_per_day=9000),
    Stock("INSW", "International Seaways", "Crude Tanker", "NYSE", opex_per_day=8600),
    # Product Tankers
    Stock("STNG", "Scorpio Tankers", "Product Tanker", "NYSE", opex_per_day=8200),
    Stock("TRMD", "TORM plc", "Product Tanker", "NASDAQ", opex_per_day=7800),
    Stock("HAFNI.OL", "Hafnia Ltd", "Product Tanker", "Oslo", currency="NOK", opex_per_day=7600),
    # Dry Bulk  (GOGL merged into FRO 2024 — removed)
    Stock("SBLK", "Star Bulk Carriers", "Dry Bulk", "NASDAQ", opex_per_day=6800),
    Stock("EGLE", "Eagle Bulk Shipping", "Dry Bulk", "NASDAQ", opex_per_day=6500),
    # LNG / LPG
    Stock("GLNG", "Golar LNG", "LNG", "NASDAQ", opex_per_day=14000),
    Stock("SFL", "SFL Corporation", "Diversified", "NYSE", opex_per_day=9500),
    # Container
    Stock("ZIM", "ZIM Integrated", "Container", "NYSE", opex_per_day=11000),
    # Diversified
    Stock("NMM", "Navios Maritime Partners", "Diversified", "NYSE", opex_per_day=8000),
]

SECTORS = sorted({s.sector for s in UNIVERSE})
TICKERS = [s.ticker for s in UNIVERSE]
TICKER_MAP: dict[str, Stock] = {s.ticker: s for s in UNIVERSE}

# Sector → rate index used for rate momentum scoring
SECTOR_RATE_INDEX = {
    "Crude Tanker": "BDTI",
    "Product Tanker": "BCTI",
    "Dry Bulk": "BDI",
    "LNG": "LNG_PROXY",
    "Container": "SCFI_PROXY",
    "Diversified": "BDI",
}

# Historical NAV multiple ranges [trough, mean, peak]
SECTOR_NAV_RANGES = {
    "Crude Tanker":   (0.45, 0.92, 1.75),
    "Product Tanker": (0.50, 0.95, 1.80),
    "Dry Bulk":       (0.40, 0.88, 1.70),
    "LNG":            (0.70, 1.10, 1.60),
    "Container":      (0.35, 0.80, 2.50),
    "Diversified":    (0.45, 0.90, 1.65),
}
