"""Tests d'Alembic : migration de base aller-retour sur la base de test."""

from __future__ import annotations

import asyncio
from pathlib import Path

import asyncpg
from alembic.config import Config

from alembic import command

BACKEND_ROOT = Path(__file__).parents[1]
BASELINE_REVISION = "0001"


def _as_raw_pg_url(database_url: str) -> str:
    """asyncpg parle postgresql:// ; SQLAlchemy utilise postgresql+asyncpg://."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def _fetch(sql: str, database_url: str) -> object | None:
    conn = await asyncpg.connect(_as_raw_pg_url(database_url))
    try:
        return await conn.fetchval(sql)
    finally:
        await conn.close()


def test_upgrade_head_then_downgrade_base_round_trip(test_database_url: str) -> None:
    config = _alembic_config(test_database_url)

    command.upgrade(config, "head")

    revision = asyncio.run(_fetch("SELECT version_num FROM alembic_version", test_database_url))
    assert revision == BASELINE_REVISION
    table_exists = asyncio.run(_fetch("SELECT to_regclass('organizations')", test_database_url))
    assert table_exists is None  # la baseline ne crée aucune table métier (phase 2)

    command.downgrade(config, "base")

    # Alembic vide l'historique mais conserve la table : la baseline ne crée aucune table
    # métier, donc vérifier l'absence de version suffit (constaté, pas supposé).
    version = asyncio.run(_fetch("SELECT version_num FROM alembic_version", test_database_url))
    assert version is None
    table_exists = asyncio.run(_fetch("SELECT to_regclass('organizations')", test_database_url))
    assert table_exists is None
