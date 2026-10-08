"""Connexion avec A2F activée : défi TOTP, code de secours, anti-rejeu, rate limit."""

from __future__ import annotations

import httpx

from app.core.constants import (
    ACCESS_COOKIE,
    API_PREFIX,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    TWO_FACTOR_COOKIE,
)
from app.core.rate_limit import TWO_FACTOR_VERIFY_RATE_LIMIT
from app.core.totp import totp_at
from tests.conftest import register_client

VALID_PASSWORD = "mot-de-passe-secret"


async def _enable_and_keep(client: httpx.AsyncClient) -> tuple[str, list[str]]:
    """Active l'A2F et retourne (secret, codes de secours)."""
    await register_client(client)
    csrf = client.cookies.get(CSRF_COOKIE)
    body = (
        await client.post(
            f"{API_PREFIX}/auth/2fa/enable",
            json={"current_password": VALID_PASSWORD},
            headers={"x-csrf-token": csrf},
        )
    ).json()
    client.cookies.clear()
    return body["secret"], body["backup_codes"]


async def _login(client: httpx.AsyncClient) -> httpx.Response:
    return await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "admin@example.com", "password": VALID_PASSWORD},
    )


async def _verify(client: httpx.AsyncClient, code: str) -> httpx.Response:
    return await client.post(f"{API_PREFIX}/auth/2fa/verify", json={"code": code})


async def test_login_with_totp_enabled_returns_a_challenge_without_a_session(
    client: httpx.AsyncClient,
) -> None:
    secret, _ = await _enable_and_keep(client)

    response = await _login(client)

    assert response.status_code == 200
    assert response.json()["totp_required"] is True
    assert response.json()["user"] is None
    assert ACCESS_COOKIE not in client.cookies
    assert REFRESH_COOKIE not in client.cookies
    assert TWO_FACTOR_COOKIE in client.cookies
    assert totp_at(secret)  # le secret capturé est bien exploitable


async def test_verify_with_a_valid_totp_issues_a_session_and_consumes_the_challenge(
    client: httpx.AsyncClient,
) -> None:
    secret, _ = await _enable_and_keep(client)
    await _login(client)
    challenge = client.cookies.get(TWO_FACTOR_COOKIE)

    response = await _verify(client, totp_at(secret))

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "admin@example.com"
    assert ACCESS_COOKIE in client.cookies and CSRF_COOKIE in client.cookies
    assert TWO_FACTOR_COOKIE not in client.cookies
    assert (await client.get(f"{API_PREFIX}/auth/me")).status_code == 200

    # Le défi est à usage unique : rejouer le même cookie et le même code échoue.
    client.cookies.clear()
    client.cookies.set(TWO_FACTOR_COOKIE, challenge)
    replay = await _verify(client, totp_at(secret))
    assert replay.status_code == 401


async def test_verify_without_a_challenge_cookie_is_rejected(client: httpx.AsyncClient) -> None:
    response = await _verify(client, "123456")

    assert response.status_code == 401


async def test_verify_with_a_wrong_totp_is_rejected(client: httpx.AsyncClient) -> None:
    secret, _ = await _enable_and_keep(client)
    await _login(client)

    response = await _verify(client, "000000")

    assert response.status_code == 401
    assert ACCESS_COOKIE not in client.cookies


async def test_a_backup_code_logs_in_and_cannot_be_replayed(client: httpx.AsyncClient) -> None:
    _, backup_codes = await _enable_and_keep(client)
    code = backup_codes[0]

    await _login(client)
    first = await _verify(client, code)

    assert first.status_code == 200
    assert (await client.get(f"{API_PREFIX}/auth/me")).status_code == 200

    # Le code de secours était consommé : une seconde connexion avec lui échoue.
    client.cookies.clear()
    await _login(client)
    replay = await _verify(client, code)
    assert replay.status_code == 401


async def test_verify_is_rate_limited_even_with_a_valid_code(client: httpx.AsyncClient) -> None:
    secret, _ = await _enable_and_keep(client)
    await _login(client)

    for _ in range(TWO_FACTOR_VERIFY_RATE_LIMIT):
        attempt = await _verify(client, "000000")
        assert attempt.status_code == 401

    blocked = await _verify(client, totp_at(secret))

    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1


async def test_login_without_totp_keeps_the_previous_flow(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()

    response = await _login(client)

    assert response.status_code == 200
    assert response.json()["totp_required"] is False
    assert ACCESS_COOKIE in client.cookies
    assert TWO_FACTOR_COOKIE not in client.cookies
