"""Tests for application configuration (env vars, defaults, validation)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

CONFIG_ENV_VARS = [
    "APP_ENV",
    "LOG_LEVEL",
    "DATASF_BASE_URL",
    "DATASF_TIMEOUT_SECONDS",
    "CACHE_TTL_SECONDS",
    "CORS_ORIGINS",
]


def test_default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in CONFIG_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "Food Truck Finder API"
    assert settings.app_version == "1.0.0"
    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.datasf_base_url == "https://data.sfgov.org/resource/rqzj-sfat.json"
    assert settings.datasf_timeout_seconds == 10.0
    assert settings.cache_ttl_seconds == 300
    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("DATASF_BASE_URL", "https://example.test/trucks.json")
    monkeypatch.setenv("DATASF_TIMEOUT_SECONDS", "3")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "60")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")

    settings = Settings(_env_file=None)

    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.datasf_base_url == "https://example.test/trucks.json"
    assert settings.datasf_timeout_seconds == 3.0
    assert settings.cache_ttl_seconds == 60
    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_cors_origins_are_parsed_and_trimmed() -> None:
    settings = Settings(cors_origins="http://a.com, http://b.com,http://c.com", _env_file=None)
    assert settings.cors_origin_list == ["http://a.com", "http://b.com", "http://c.com"]


def test_empty_cors_origins_yield_empty_list() -> None:
    settings = Settings(cors_origins="", _env_file=None)
    assert settings.cors_origin_list == []


@pytest.mark.parametrize("log_level", ["VERBOSE", "trace", "Info5"])
def test_invalid_log_level_rejected(log_level: str) -> None:
    with pytest.raises(ValidationError):
        Settings(log_level=log_level, _env_file=None)


def test_invalid_app_env_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="staging", _env_file=None)


@pytest.mark.parametrize("timeout", [0, -1, -5.5])
def test_non_positive_timeout_rejected(timeout: float) -> None:
    with pytest.raises(ValidationError):
        Settings(datasf_timeout_seconds=timeout, _env_file=None)


@pytest.mark.parametrize("ttl", [-1, -100])
def test_negative_cache_ttl_rejected(ttl: int) -> None:
    with pytest.raises(ValidationError):
        Settings(cache_ttl_seconds=ttl, _env_file=None)