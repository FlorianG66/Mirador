"""Mot de passe oublié : jeton à usage unique, révocation des sessions, anti-énumération."""

from __future__ import annotations

import re

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import ACCESS_COOKIE, API_PREFIX
from app.core.rate_limit import PASSWORD_FORGOT_RATE_LIMIT
from app.core.security import generate_token, hash_token
from tests.conftest import register_client

VALID_PASSWORD = "mot-de-passe-secret"
NEW_PASSWORD = "nouveau-mot-de-passe-secret"


class FakeEmailSender:
    """Capture les e-mails : les assertions portent sur le contenu, sans SMTP."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, *, to: str, subject: str, content: str) -> None:
        self.sent.append((to, subject, content))


def _extract_token(content: str) -> str:
    match = re.search(r"reset-password\?token=([^\s]+)", content)
    assert match is not None, "l'e-mail doit contenir le lien de réinitialisation"
    return match.group(1)


async def _forgot(client: httpx.AsyncClient, email: str) -> httpx.Response:
    return await client.post(f"{API_PREFIX}/auth/password/forgot", json={"email": email})


async def _reset(
    client: httpx.AsyncClient, token: str, password: str = NEW_PASSWORD
) -> httpx.Response:
    return await client.post(
        f"{API_PREFIX}/auth/password/reset", json={"token": token, "new_password": password}
    )


async def test_forgot_returns_the_same_answer_whether_or_not_the_email_exists(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    await register_client(client)
    client.cookies.clear()
    sender = FakeEmailSender()
    app.state.email_sender = sender

    known = await _forgot(client, "admin@example.com")
    unknown = await _forgot(client, "absent@example.com")

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"status": "ok"}
    assert len(sender.sent) == 1  # réservé au compte existant : pas d'énumération


async def test_forgot_stores_a_hashed_token_and_sends_the_reset_link(
    client: httpx.AsyncClient,
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_client(client)
    client.cookies.clear()
    sender = FakeEmailSender()
    app.state.email_sender = sender

    await _forgot(client, "admin@example.com")

    to, subject, content = sender.sent[0]
    assert to == "admin@example.com"
    raw_token = _extract_token(content)
    async with session_factory() as session:
        digest = (
            await session.execute(text("SELECT token_hash FROM password_reset_tokens"))
        ).scalar_one()
    assert digest == hash_token(raw_token)
    assert digest != raw_token


async def test_reset_with_a_valid_token_changes_the_password_and_revokes_all_sessions(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    await register_client(client)
    old_access = client.cookies.get(ACCESS_COOKIE)
    client.cookies.clear()
    sender = FakeEmailSender()
    app.state.email_sender = sender
    await _forgot(client, "admin@example.com")

    response = await _reset(client, _extract_token(sender.sent[0][2]))

    assert response.status_code == 200
    # Toutes les sessions sont révoquées, y compris celle du test.
    client.cookies.set(ACCESS_COOKIE, old_access)
    assert (await client.get(f"{API_PREFIX}/auth/me")).status_code == 401

    client.cookies.clear()
    old_login = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "admin@example.com", "password": VALID_PASSWORD},
    )
    new_login = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "admin@example.com", "password": NEW_PASSWORD},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


async def test_a_reset_token_cannot_be_replayed(client: httpx.AsyncClient, app: FastAPI) -> None:
    await register_client(client)
    client.cookies.clear()
    sender = FakeEmailSender()
    app.state.email_sender = sender
    await _forgot(client, "admin@example.com")
    token = _extract_token(sender.sent[0][2])

    first = await _reset(client, token)
    replay = await _reset(client, token)

    assert first.status_code == 200
    assert replay.status_code == 401


async def test_an_expired_reset_token_is_rejected(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    register = await register_client(client)
    user_id = register.json()["user"]["id"]
    raw_token = generate_token()
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)"
                " VALUES (:user_id, :token_hash, now() - interval '1 minute')"
            ),
            {"user_id": user_id, "token_hash": hash_token(raw_token)},
        )
        await session.commit()
    client.cookies.clear()

    response = await _reset(client, raw_token)

    assert response.status_code == 401


async def test_a_fabricated_reset_token_is_rejected(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()

    response = await _reset(client, "jeton-invente")

    assert response.status_code == 401


async def test_reset_rejects_a_too_short_new_password(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()

    response = await _reset(client, "jeton-invente", password="court")

    assert response.status_code == 422


async def test_forgot_is_rate_limited(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()

    for _ in range(PASSWORD_FORGOT_RATE_LIMIT):
        attempt = await _forgot(client, "admin@example.com")
        assert attempt.status_code == 200

    blocked = await _forgot(client, "admin@example.com")

    assert blocked.status_code == 429
