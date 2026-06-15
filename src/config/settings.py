from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    fred_api_key: str = ""
    price_refresh_minutes: int = 30
    data_dir: str = "data"
    db_path: str = "data/shipping.db"

    # Rate index series IDs on FRED
    bdi_series: str = "BDIY"
    bdti_series: str = "BDTI"

    # Model params
    rate_forecast_horizon_days: int = 90
    nav_confidence: float = 0.85


settings = Settings()
