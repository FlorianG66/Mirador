"""Fixtures partagées : application sous test et base PostgreSQL isolée par session."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pgserver
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.main import create_app

# URL volontairement injoignable : port 1 = refus de connexion immédiat.
UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://mirador:mirador@127.0.0.1:1/mirador"


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    """Base PostgreSQL réelle, isolée et jetable : créée une fois par session de tests."""
    datadir = Path(tempfile.mkdtemp(prefix="mirador-pg-"))
    server = pgserver.get_server(str(datadir))
    try:
        # pgserver expose postgresql:// ; SQLAlchemy a besoin du dialecte +asyncpg.
        yield server.get_uri().replace("postgresql://", "postgresql+asyncpg://", 1)
    finally:
        server.cleanup()


@pytest.fixture
def app(test_database_url: str) -> FastAPI:
    """Application branchée sur la base de test."""
    return create_app(Settings(database_url=test_database_url))


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Client HTTP ASGI contre l'application sous test."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
