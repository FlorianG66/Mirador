"""Tests de la configuration (pydantic-settings) : défauts, variables et validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings

ENV_EXAMPLE_PATH = Path(__file__).parents[2] / ".env.example"


def test_settings_have_documented_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000


def test_settings_read_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db:5432/mirador")
    monkeypatch.setenv("API_PORT", "9000")

    settings = Settings(_env_file=None)

    assert settings.environment == "production"
    assert settings.log_level == "WARNING"
    assert settings.database_url == "postgresql+asyncpg://user:pass@db:5432/mirador"
    assert settings.api_port == 9000


def test_settings_reject_database_url_without_asyncpg_scheme() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(database_url="sqlite:///local.db", _env_file=None)

    assert "postgresql+asyncpg://" in str(exc_info.value)


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="staging", _env_file=None)  # type: ignore[arg-type]


def test_settings_reject_unknown_log_level() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="VERBOSE", _env_file=None)  # type: ignore[arg-type]


def test_settings_ignore_unknown_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le même environnement sert au backend et à d'autres services : pas d'échec sur l'inconnu."""
    monkeypatch.setenv("UNRELATED_VAR", "valeur")

    settings = Settings(_env_file=None)

    assert settings.environment == "development"


def test_get_settings_returns_the_cached_instance() -> None:
    assert get_settings() is get_settings()


def test_every_settings_field_is_documented_in_env_example() -> None:
    """Non-régression : .env.example et Settings ne doivent pas diverger."""
    content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    documented_keys = {
        line.split("=", 1)[0].strip().upper()
        for line in content.splitlines()
        if "=" in line and not line.strip().startswith("#")
    }

    fields = {field.upper() for field in Settings.model_fields}

    assert fields <= documented_keys, f"champs absents de .env.example : {fields - documented_keys}"
