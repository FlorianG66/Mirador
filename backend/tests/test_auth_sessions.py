"""Sessions : rotation du jeton de rafraîchissement, révocation, expiration."""

from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import ACCESS_COOKIE, API_PREFIX, CSRF_COOKIE, REFRESH_COOKIE
from tests.conftest import register_client


async def _logout(client: httpx.AsyncClient, csrf: str) -> httpx.Response:
    return await client.post(f"{API_PREFIX}/auth/logout", headers={"x-csrf-token": csrf})


async def test_refresh_rotates_both_tokens(client: httpx.AsyncClient) -> None:
    await register_client(client)
    old_access, old_refresh, csrf = (
        client.cookies.get(ACCESS_COOKIE),
        client.cookies.get(REFRESH_COOKIE),
        client.cookies.get(CSRF_COOKIE),
    )

    response = await client.post(f"{API_PREFIX}/auth/refresh", headers={"x-csrf-token": csrf})

    assert response.status_code == 200
    assert client.cookies.get(ACCESS_COOKIE) != old_access
    assert client.cookies.get(REFRESH_COOKIE) != old_refresh
    # Le jeton CSRF appartient à la session, pas à l'accès : il ne tourne pas.
    assert client.cookies.get(CSRF_COOKIE) == csrf


async def test_a_stolen_old_refresh_token_is_rejected(client: httpx.AsyncClient) -> None:
    await register_client(client)
    csrf = client.cookies.get(CSRF_COOKIE)
    stolen_refresh = client.cookies.get(REFRESH_COOKIE)
    rotated = await client.post(f"{API_PREFIX}/auth/refresh", headers={"x-csrf-token": csrf})
    assert rotated.status_code == 200

    # Rejeu du jeton d'avant la rotation : le hachage en base a changé.
    client.cookies.delete(REFRESH_COOKIE)
    client.cookies.set(REFRESH_COOKIE, stolen_refresh)
    replay = await client.post(
        f"{API_PREFIX}/auth/refresh", headers={"x-csrf-token": client.cookies.get(CSRF_COOKIE)}
    )

    assert replay.status_code == 401


async def test_refresh_without_cookie_is_unauthorized(client: httpx.AsyncClient) -> None:
    response = await client.post(f"{API_PREFIX}/auth/refresh")

    assert response.status_code == 401


async def test_logout_revokes_the_session(client: httpx.AsyncClient) -> None:
    await register_client(client)
    csrf = client.cookies.get(CSRF_COOKIE)
    stolen_access = client.cookies.get(ACCESS_COOKIE)
    stolen_refresh = client.cookies.get(REFRESH_COOKIE)

    response = await _logout(client, csrf)

    assert response.status_code == 204
    assert ACCESS_COOKIE not in client.cookies
    assert REFRESH_COOKIE not in client.cookies

    # Les jetons conservés de côté ne fonctionnent plus : la session est révoquée.
    client.cookies.set(ACCESS_COOKIE, stolen_access)
    assert (await client.get(f"{API_PREFIX}/auth/me")).status_code == 401

    client.cookies.set(REFRESH_COOKIE, stolen_refresh)
    client.cookies.set(CSRF_COOKIE, csrf)
    replay = await client.post(f"{API_PREFIX}/auth/refresh", headers={"x-csrf-token": csrf})
    assert replay.status_code == 401


async def test_an_expired_access_token_is_rejected(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_client(client)
    async with session_factory() as session:
        await session.execute(
            text("UPDATE sessions SET access_expires_at = now() - interval '1 h'")
        )
        await session.commit()

    response = await client.get(f"{API_PREFIX}/auth/me")

    assert response.status_code == 401


async def test_an_expired_refresh_token_is_rejected(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_client(client)
    csrf = client.cookies.get(CSRF_COOKIE)
    async with session_factory() as session:
        await session.execute(
            text("UPDATE sessions SET refresh_expires_at = now() - interval '1 h'")
        )
        await session.commit()

    response = await client.post(f"{API_PREFIX}/auth/refresh", headers={"x-csrf-token": csrf})

    assert response.status_code == 401
