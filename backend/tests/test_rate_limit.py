"""Rate limiting sur l'authentification : 429 + Retry-After, limité par route et par IP."""

from __future__ import annotations

import httpx

from app.core.constants import API_PREFIX
from app.core.rate_limit import LOGIN_RATE_LIMIT, REGISTER_RATE_LIMIT
from tests.conftest import register_client


async def test_login_is_rate_limited_after_too_many_attempts(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()
    credentials = {"email": "admin@example.com", "password": "mot-de-passe-faux"}

    for _ in range(LOGIN_RATE_LIMIT):
        attempt = await client.post(f"{API_PREFIX}/auth/login", json=credentials)
        assert attempt.status_code == 401

    # La tentative suivante est refusée avant même de vérifier le mot de passe.
    blocked = await client.post(f"{API_PREFIX}/auth/login", json=credentials)

    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1


async def test_register_is_rate_limited(client: httpx.AsyncClient) -> None:
    for index in range(REGISTER_RATE_LIMIT):
        response = await register_client(client, email=f"compte{index}@example.com")
        assert response.status_code == 201

    blocked = await register_client(client, email="trop@example.com")

    assert blocked.status_code == 429
    assert blocked.headers["content-type"].startswith("application/problem+json")


async def test_the_rate_limit_of_login_does_not_block_register(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()
    credentials = {"email": "admin@example.com", "password": "mot-de-passe-faux"}
    for _ in range(LOGIN_RATE_LIMIT):
        await client.post(f"{API_PREFIX}/auth/login", json=credentials)

    response = await register_client(client, email="autre@example.com")

    assert response.status_code == 201
