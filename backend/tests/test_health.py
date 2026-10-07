"""Tests de l'API de santé : vivacité et état de la base."""

from __future__ import annotations

import httpx

from app.core.constants import API_SERVICE, API_VERSION


async def test_health_returns_200_with_status_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == API_SERVICE
    assert data["version"] == API_VERSION


async def test_health_works_without_database(client: httpx.AsyncClient) -> None:
    """La vivacité ne dépend pas de PostgreSQL : elle doit répondre quoi qu'il arrive."""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


async def test_health_db_returns_server_version(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health/db")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"]["status"] == "ok"
    assert "PostgreSQL" in data["database"]["server_version"]


async def test_health_db_returns_503_when_database_unreachable() -> None:
    """Base injoignable : problème RFC 9457 en 503, jamais d'erreur 500 brute."""
    from app.core.config import Settings
    from app.main import create_app
    from tests.conftest import UNREACHABLE_DATABASE_URL

    app = create_app(Settings(database_url=UNREACHABLE_DATABASE_URL))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/db")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 503
