"""Application settings loaded from environment variables and .env.

Values can be overridden via environment variables at runtime, which takes
precedence over the local ``backend/.env`` file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings(BaseSettings):
    """Centralized configuration for the Food Truck Finder backend."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Food Truck Finder API"
    app_version: str = "1.0.0"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # DataSF Food Trucks API
    datasf_base_url: str = "https://data.sfgov.org/resource/rqzj-sfat.json"
    datasf_timeout_seconds: float = Field(default=10.0, gt=0)

    # Caching
    cache_ttl_seconds: int = Field(default=300, ge=0)

    # CORS
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in VALID_LOG_LEVELS:
            raise ValueError(
                f"invalid LOG_LEVEL '{value}'; must be one of {sorted(VALID_LOG_LEVELS)}"
            )
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a parsed list, ignoring empty entries."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton per process)."""
    return Settings()