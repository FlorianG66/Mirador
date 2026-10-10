"""Configuration applicative via pydantic-settings (variables d'environnement + .env)."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import API_PREFIX

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
    # Connexion Google (phase 2e) : vide = fournisseur non branché (404 sur les routes).
    google_client_id: str = ""
    google_client_secret: str = ""
    # Worker de données fictives (phase 4) : intervalle de synchronisation des
    # connecteurs, en minutes. 0 = planificateur désactivé (ex. tests).
    sync_interval_minutes: int = 5

    @property
    def google_redirect_uri(self) -> str:
        """URI de retour : elle doit être enregistrée à l'identique chez Google.

        On suppose l'application servie depuis une seule origine (`app_base_url`),
        le frontend et l'API partageant le domaine — voir docs/DECISIONS.md.
        """
        return f"{self.app_base_url}{API_PREFIX}/auth/google/callback"

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
