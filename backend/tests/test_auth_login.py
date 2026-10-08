"""Connexion e-mail/mot de passe et accès à l'utilisateur courant."""

from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import ACCESS_COOKIE, API_PREFIX
from tests.conftest import register_client


async def test_login_with_valid_credentials_returns_the_user(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()

    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "admin@example.com", "password": "mot-de-passe-secret"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "admin@example.com"
    assert ACCESS_COOKIE in client.cookies
    me = await client.get(f"{API_PREFIX}/auth/me")
    assert me.status_code == 200


async def test_login_with_a_wrong_password_sets_no_cookie(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()

    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "admin@example.com", "password": "mot-de-passe-faux"},
    )

    assert response.status_code == 401
    assert ACCESS_COOKIE not in client.cookies


async def test_login_never_says_whether_the_email_exists(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()

    wrong_password = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "admin@example.com", "password": "mot-de-passe-faux"},
    )
    unknown_email = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "absent@example.com", "password": "mot-de-passe-secret"},
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


async def test_a_passwordless_account_cannot_use_the_password_form(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Compte créé via Google OIDC (aucun mot de passe local) : la connexion échoue."""
    async with session_factory() as session:
        await session.execute(
            text("INSERT INTO users (email, password_hash) VALUES ('oidc@example.com', NULL)")
        )
        await session.commit()

    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "oidc@example.com", "password": "mot-de-passe-secret"},
    )

    assert response.status_code == 401


async def test_me_without_cookie_is_unauthorized(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{API_PREFIX}/auth/me")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_me_with_a_forged_cookie_is_unauthorized(client: httpx.AsyncClient) -> None:
    await register_client(client)
    client.cookies.clear()
    client.cookies.set(ACCESS_COOKIE, "jeton-invente")

    response = await client.get(f"{API_PREFIX}/auth/me")

    assert response.status_code == 401
