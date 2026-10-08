"""Configuration applicative via pydantic-settings (variables d'environnement + .env)."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DATABASE_URL_PREFIX = "postgresql+asyncpg://"

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Paramètres de l'application, lus depuis l'environnement puis `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Environment = "development"
    log_level: LogLevel = "INFO"
    database_url: str = DATABASE_URL_PREFIX + "mirador:mirador-dev-local@localhost:5432/mirador"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    # Base publique de l'application : préfixe des liens envoyés par e-mail
    # (réinitialisation de mot de passe, plus tard invitations) — phase 2c.
    app_base_url: str = "http://localhost:8000"

    @field_validator("database_url")
    @classmethod
    def _database_url_uses_asyncpg(cls, value: str) -> str:
        """Un seul dialecte : asyncpg (spec §5.2, SQLAlchemy async)."""
        if not value.startswith(DATABASE_URL_PREFIX):
            raise ValueError(f"DATABASE_URL doit commencer par {DATABASE_URL_PREFIX}")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instance unique de configuration (cache : lue une seule fois par processus)."""
    return Settings()
