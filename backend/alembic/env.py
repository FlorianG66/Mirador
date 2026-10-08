"""Environnement Alembic : migrations asynchrones via SQLAlchemy 2."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Rend `import app` possible quelle que soit la commande lancée (racine : backend/).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402  # importe tous les modèles dans Base.metadata

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    """URL prioritaire : celle passée par la commande, sinon celle des settings."""
    url = config.get_main_option("sqlalchemy.url")
    return url if url else get_settings().database_url


def _run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Point d'entrée utilisé par les commandes `alembic upgrade/downgrade`."""
    asyncio.run(_run_async_migrations())


run_migrations_online()
