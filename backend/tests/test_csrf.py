"""Protection CSRF : double submit cookie + en-tête, sauf sur l'entrée en sanctuaire."""

from __future__ import annotations

import httpx

from app.core.constants import API_PREFIX, CSRF_COOKIE
from tests.conftest import register_client


async def test_logout_without_the_csrf_header_is_forbidden(client: httpx.AsyncClient) -> None:
    await register_client(client)

    response = await client.post(f"{API_PREFIX}/auth/logout")

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_logout_with_a_wrong_csrf_token_is_forbidden(client: httpx.AsyncClient) -> None:
    await register_client(client)

    response = await client.post(
        f"{API_PREFIX}/auth/logout", headers={"x-csrf-token": "faux-jeton"}
    )

    assert response.status_code == 403


async def test_logout_with_the_real_csrf_token_succeeds(client: httpx.AsyncClient) -> None:
    await register_client(client)

    response = await client.post(
        f"{API_PREFIX}/auth/logout",
        headers={"x-csrf-token": client.cookies.get(CSRF_COOKIE, "")},
    )

    assert response.status_code == 204


async def test_refresh_also_requires_the_csrf_token(client: httpx.AsyncClient) -> None:
    await register_client(client)

    response = await client.post(f"{API_PREFIX}/auth/refresh")

    assert response.status_code == 403


async def test_login_is_exempt_from_csrf(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()

    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "admin@example.com", "password": "mot-de-passe-secret"},
    )

    assert response.status_code == 200
