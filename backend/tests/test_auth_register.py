"""Inscription : crée le compte, l'organisation et le rattachement admin."""

from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import ACCESS_COOKIE, API_PREFIX, CSRF_COOKIE, REFRESH_COOKIE
from tests.conftest import register_client


def _cookie_headers(response: httpx.Response) -> list[str]:
    return response.headers.get_list("set-cookie")


async def test_register_creates_account_and_sets_cookies(client: httpx.AsyncClient) -> None:
    response = await register_client(client)

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "admin@example.com"
    assert body["organization"]["name"] == "Acme"

    cookies = _cookie_headers(response)
    access = next(c for c in cookies if c.startswith(f"{ACCESS_COOKIE}="))
    refresh = next(c for c in cookies if c.startswith(f"{REFRESH_COOKIE}="))
    csrf = next(c for c in cookies if c.startswith(f"{CSRF_COOKIE}="))
    assert "HttpOnly" in access and "Path=/" in access and "SameSite=lax" in access
    # Le jeton de rafraîchissement ne quitte jamais la route d'authentification.
    assert "HttpOnly" in refresh and "Path=/api/v1/auth" in refresh
    # Le jeton CSRF se lit depuis le JS : jamais httpOnly.
    assert "HttpOnly" not in csrf


async def test_register_normalizes_the_email(client: httpx.AsyncClient) -> None:
    response = await register_client(client, email="Admin@Example.COM")

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "admin@example.com"
    me = await client.get(f"{API_PREFIX}/auth/me")
    assert me.json()["email"] == "admin@example.com"


async def test_register_makes_the_creator_an_admin(client: httpx.AsyncClient) -> None:
    await register_client(client)

    me = await client.get(f"{API_PREFIX}/auth/me")

    assert me.status_code == 200
    memberships = me.json()["memberships"]
    assert len(memberships) == 1
    assert memberships[0]["role"] == "admin"


async def test_register_rejects_a_duplicate_email(client: httpx.AsyncClient) -> None:
    await register_client(client)

    response = await register_client(client, organization_name="Autre")

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_register_rejects_an_invalid_email(client: httpx.AsyncClient) -> None:
    response = await register_client(client, email="pas-un-email")

    assert response.status_code == 422


async def test_register_rejects_a_short_password(client: httpx.AsyncClient) -> None:
    response = await register_client(client, password="court")

    assert response.status_code == 422


async def test_register_rejects_an_invalid_siren(client: httpx.AsyncClient) -> None:
    response = await register_client(client, siren="123456789")

    assert response.status_code == 422


async def test_register_stores_a_valid_siren(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    response = await register_client(client, siren="123456782")

    assert response.status_code == 201
    async with session_factory() as session:
        siren = await session.execute(text("SELECT siren FROM organizations"))
        assert siren.scalar_one() == "123456782"


async def test_register_without_siren_leaves_it_empty(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    response = await register_client(client)

    assert response.status_code == 201
    async with session_factory() as session:
        siren = await session.execute(text("SELECT siren FROM organizations"))
        assert siren.scalar_one() is None
