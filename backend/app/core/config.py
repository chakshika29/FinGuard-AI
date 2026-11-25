"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Central configuration for FinGuard AI."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "FinGuard AI"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Security
    JWT_SECRET_KEY: str = "change-this-to-a-long-random-secret-key-at-least-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    DEMO_ADMIN_PASSWORD: str = "Admin@FinGuard2026!"
    DEMO_STEWARD_PASSWORD: str = "Steward@FinGuard2026!"
    DEMO_ANALYST_PASSWORD: str = "Analyst@FinGuard2026!"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    # Backend Mode: "local" or "bigquery"
    DATA_BACKEND: str = "local"

    # Local Paths
    LOCAL_DUCKDB_PATH: str = "data/processed/finguard_warehouse.duckdb"
    LOCAL_METADATA_DB_URL: str = "sqlite:///./data/processed/finguard_metadata.db"
    DATA_RAW_DIR: str = "data/raw"
    DATA_PROCESSED_DIR: str = "data/processed"
    DATA_SAMPLE_DIR: str = "data/sample"
    POWERBI_EXPORT_DIR: str = "powerbi/datasets"

    # GCP / BigQuery
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "US"
    GCS_BUCKET_NAME: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    BIGQUERY_RAW_DATASET: str = "finguard_raw"
    BIGQUERY_STAGING_DATASET: str = "finguard_staging"
    BIGQUERY_CURATED_DATASET: str = "finguard_curated"
    BIGQUERY_GOVERNANCE_DATASET: str = "finguard_governance"
    BIGQUERY_ANALYTICS_DATASET: str = "finguard_analytics"

    MAX_UPLOAD_SIZE_MB: int = 250
    DEFAULT_RANDOM_SEED: int = 42

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def resolve_path(self, relative_or_abs: str) -> Path:
        p = Path(relative_or_abs)
        if p.is_absolute():
            return p
        return (PROJECT_ROOT / p).resolve()

    @property
    def duckdb_path(self) -> Path:
        return self.resolve_path(self.LOCAL_DUCKDB_PATH)

    @property
    def metadata_db_url(self) -> str:
        url = self.LOCAL_METADATA_DB_URL
        if url.startswith("sqlite:///./"):
            rel = url.replace("sqlite:///./", "")
            abs_path = self.resolve_path(rel)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{abs_path.as_posix()}"
        return url

    @property
    def raw_dir(self) -> Path:
        p = self.resolve_path(self.DATA_RAW_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def processed_dir(self) -> Path:
        p = self.resolve_path(self.DATA_PROCESSED_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def sample_dir(self) -> Path:
        p = self.resolve_path(self.DATA_SAMPLE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def powerbi_dir(self) -> Path:
        p = self.resolve_path(self.POWERBI_EXPORT_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def is_bigquery_mode(self) -> bool:
        return self.DATA_BACKEND.lower() == "bigquery" and bool(self.GCP_PROJECT_ID)


@lru_cache
def get_settings() -> Settings:
    return Settings()
