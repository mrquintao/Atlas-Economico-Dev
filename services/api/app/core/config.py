from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://atlas:atlas@localhost:5432/atlas"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"
    log_json: bool = True

    # Outbound HTTP to official sources
    http_timeout_seconds: float = 30.0
    http_max_retries: int = 4
    http_backoff_base_seconds: float = 1.0
    http_user_agent: str = (
        "AtlasEconomicoBrasileiro/0.1 (+https://github.com/mrquintao/atlas-economico-dev)"
    )
    bcb_sgs_base_url: str = "https://api.bcb.gov.br/dados/serie"
    ibge_sidra_base_url: str = "https://apisidra.ibge.gov.br"
    ibge_malhas_base_url: str = "https://servicodados.ibge.gov.br/api/v3/malhas"
    # Edition (year) of the IBGE state mesh collected by `ingest-boundaries` (latest served: 2022).
    ibge_mesh_year: int = Field(default=2022, ge=2000)
    # Window size for daily SGS series. The official limit is 10 years per request, but large
    # windows take ~30 s and frequently time out; 1-year windows answer in ~1 s.
    bcb_daily_window_years: int = Field(default=1, ge=1, le=10)
    # Minimum interval between two requests to the same source (seconds).
    bcb_min_request_interval_seconds: float = 0.5
    ibge_min_request_interval_seconds: float = 0.5

    # Scheduled collection (Compose `scheduler` service): times of day, Brasília time.
    ingest_schedule: str = "06:00"
    # Also collect once as soon as the scheduler starts (e.g. to fill a fresh database).
    ingest_on_start: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
