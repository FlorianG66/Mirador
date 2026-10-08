"""Édition de l'A2F : activation, désactivation, codes de secours, protection CSRF."""

from __future__ import annotations

import base64
import hashlib

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import API_PREFIX, CSRF_COOKIE
from app.core.totp import generate_totp_secret
from tests.conftest import register_client

BACKUP_CODE_COUNT = 10
VALID_PASSWORD = "mot-de-passe-secret"


async def _enable(client: httpx.AsyncClient, password: str = VALID_PASSWORD) -> httpx.Response:
    """Poste une activation par défaut (l'e-mail du compte ADMIN@example.com)."""
    csrf = client.cookies.get(CSRF_COOKIE)
    return await client.post(
        f"{API_PREFIX}/auth/2fa/enable",
        json={"current_password": password},
        headers={"x-csrf-token": csrf},
    )


async def test_enable_requires_an_authenticated_session(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()

    response = await client.post(
        f"{API_PREFIX}/auth/2fa/enable", json={"current_password": VALID_PASSWORD}
    )

    assert response.status_code == 401


async def test_enable_requires_the_current_password(client: httpx.AsyncClient) -> None:
    await register_client(client)
    csrf = client.cookies.get(CSRF_COOKIE)

    missing = await client.post(
        f"{API_PREFIX}/auth/2fa/enable", json={}, headers={"x-csrf-token": csrf}
    )
    wrong_password = await _enable(client, password="mauvais-mot-de-passe")

    assert missing.status_code == 422
    assert wrong_password.status_code == 401


async def test_enable_is_csrf_protected(client: httpx.AsyncClient) -> None:
    await register_client(client)

    without = await client.post(
        f"{API_PREFIX}/auth/2fa/enable", json={"current_password": VALID_PASSWORD}
    )
    forged = await client.post(
        f"{API_PREFIX}/auth/2fa/enable",
        json={"current_password": VALID_PASSWORD},
        headers={"x-csrf-token": "jeton-invente"},
    )

    assert without.status_code == 403
    assert forged.status_code == 403


async def test_enable_returns_secret_uri_and_ten_backup_codes(client: httpx.AsyncClient) -> None:
    await register_client(client)

    response = await _enable(client)
    body = response.json()

    assert response.status_code == 200
    assert len(body["secret"]) == 32
    assert body["otpauth_url"].startswith("otpauth://totp/")
    assert len(body["backup_codes"]) == BACKUP_CODE_COUNT
    assert len(set(body["backup_codes"])) == BACKUP_CODE_COUNT
    assert all(len(code) == 8 for code in body["backup_codes"])


async def test_enable_persists_the_secret_and_enables_the_second_factor(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_client(client)
    secret = (await _enable(client)).json()["secret"]

    async with session_factory() as session:
        row = (await session.execute(text("SELECT totp_secret FROM users"))).one_or_none()
        enabled = (
            await session.execute(text("SELECT totp_enabled_at IS NOT NULL FROM users"))
        ).scalar_one()
        backup_rows = (
            await session.execute(text("SELECT count(*) FROM backup_codes"))
        ).scalar_one()

    assert row is not None and row[0] == secret
    assert enabled is True
    assert backup_rows == BACKUP_CODE_COUNT


async def test_backup_codes_are_stored_hashed_not_in_plaintext(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_client(client)
    backup_codes = (await _enable(client)).json()["backup_codes"]

    async with session_factory() as session:
        hashes = list(
            (await session.execute(text("SELECT code_hash FROM backup_codes ORDER BY created_at")))
            .scalars()
            .all()
        )

    assert len(hashes) == len(backup_codes)
    for code, digest in zip(backup_codes, hashes, strict=True):
        assert digest != code
        assert digest == hashlib.sha256(code.encode()).hexdigest()


async def test_enabling_again_regenerates_secret_and_backup_codes(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_client(client)
    first = (await _enable(client)).json()
    second = (await _enable(client)).json()

    assert second["secret"] != first["secret"]
    assert set(second["backup_codes"]) != set(first["backup_codes"])
    async with session_factory() as session:
        count = (await session.execute(text("SELECT count(*) FROM backup_codes"))).scalar_one()
    assert count == BACKUP_CODE_COUNT  # les codes précédents ont bien été révoqués


async def test_disable_clears_the_secret_and_revokes_the_backup_codes(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_client(client)
    await _enable(client)
    csrf = client.cookies.get(CSRF_COOKIE)

    wrong = await client.post(
        f"{API_PREFIX}/auth/2fa/disable",
        json={"current_password": "mauvais-mot-de-passe"},
        headers={"x-csrf-token": csrf},
    )
    response = await client.post(
        f"{API_PREFIX}/auth/2fa/disable",
        json={"current_password": VALID_PASSWORD},
        headers={"x-csrf-token": csrf},
    )

    assert wrong.status_code == 401
    assert response.status_code == 204
    async with session_factory() as session:
        secret = (await session.execute(text("SELECT totp_secret FROM users"))).scalar_one()
        backup_rows = (
            await session.execute(text("SELECT count(*) FROM backup_codes"))
        ).scalar_one()
    assert secret is None
    assert backup_rows == 0


async def test_generated_secret_is_a_valid_totp_secret(client: httpx.AsyncClient) -> None:
    """Le secret renvoyé est exploitable par la primitive (b32, 20 octets, aléatoire)."""
    await register_client(client)
    secret = (await _enable(client)).json()["secret"]

    assert len(base64.b32decode(secret)) == 20
    assert generate_totp_secret() != secret  # pas une constante en dur
