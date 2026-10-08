"""Connexion Google (OIDC) : démarrage, callback et garde-fous (SPEC §2, phase 2e)."""

from __future__ import annotations

import urllib.parse

import httpx
import pytest
from fastapi import FastAPI

from app.core.constants import (
    ACCESS_COOKIE,
    API_PREFIX,
    CSRF_COOKIE,
    OAUTH_STATE_COOKIE,
    REFRESH_COOKIE,
    TWO_FACTOR_COOKIE,
)
from app.core.rate_limit import GOOGLE_RATE_LIMIT
from app.services.oidc import GoogleOidcProvider, OidcIdentity, OidcProviderError
from tests.conftest import register_client
from tests.helpers import PASSWORD, install_oidc

EMAIL = "admin@example.com"
START = f"{API_PREFIX}/auth/google"
CALLBACK = f"{API_PREFIX}/auth/google/callback"
GOOGLE_ACCOUNT = OidcIdentity(
    subject="google-subject-1", email=EMAIL, email_verified=True, name="Ada Lovelace"
)


async def _start(client: httpx.AsyncClient) -> str:
    """Ouvre le parcours et retourne l'état posé dans le cookie."""
    response = await client.get(START)
    assert response.status_code == 302, response.text
    state = client.cookies.get(OAUTH_STATE_COOKIE, "")
    assert state, "le démarrage doit poser un cookie d'état"
    return state


async def _callback(client: httpx.AsyncClient, state: str, **params: str) -> httpx.Response:
    """Reviens du fournisseur avec l'état du parcours et les paramètres donnés."""
    query = urllib.parse.urlencode({"state": state, **params})
    return await client.get(f"{CALLBACK}?{query}")


async def test_start_redirects_to_google_and_sets_an_http_only_state_cookie(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    provider = install_oidc(app)

    response = await client.get(START)

    assert response.status_code == 302
    parsed = urllib.parse.urlparse(response.headers["location"])
    query = urllib.parse.parse_qs(parsed.query)
    state = client.cookies.get(OAUTH_STATE_COOKIE, "")
    assert query["state"] == [state]
    assert query["response_type"] == ["code"]
    assert query["redirect_uri"] == [
        f"{app.state.settings.app_base_url}{API_PREFIX}/auth/google/callback"
    ]
    assert provider.authorization_urls, "l'URL d'autorisation doit être construite"
    state_cookies = [
        header
        for header in response.headers.get_list("set-cookie")
        if header.startswith(f"{OAUTH_STATE_COOKIE}=")
    ]
    assert state_cookies and "HttpOnly" in state_cookies[0]
    assert f"Path={API_PREFIX}/auth" in state_cookies[0]


async def test_start_is_unavailable_when_google_is_not_configured(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.state.oidc_provider = None

    response = await client.get(START)

    assert response.status_code == 404
    assert response.json()["detail"] == "Connexion Google indisponible."


async def test_start_is_rate_limited(app: FastAPI, client: httpx.AsyncClient) -> None:
    install_oidc(app)

    for _ in range(GOOGLE_RATE_LIMIT):
        assert (await client.get(START)).status_code == 302
    response = await client.get(START)

    assert response.status_code == 429
    assert response.headers.get("retry-after")


async def test_callback_signs_in_an_existing_account(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    install_oidc(app, GOOGLE_ACCOUNT)
    await register_client(client, email=EMAIL)
    client.cookies.clear()
    state = await _start(client)

    response = await _callback(client, state, code="code-1")

    assert response.status_code == 200
    assert response.json()["totp_required"] is False
    assert response.json()["user"]["email"] == EMAIL
    assert ACCESS_COOKIE in client.cookies
    assert REFRESH_COOKIE in client.cookies
    assert OAUTH_STATE_COOKIE not in client.cookies, "l'état est à usage unique"
    me = await client.get(f"{API_PREFIX}/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


async def test_callback_sends_the_configured_redirect_uri(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    provider = install_oidc(app, GOOGLE_ACCOUNT)
    await register_client(client, email=EMAIL)
    client.cookies.clear()
    state = await _start(client)

    await _callback(client, state, code="code-1")

    expected = f"{app.state.settings.app_base_url}{API_PREFIX}/auth/google/callback"
    assert provider.exchange_calls == [("code-1", expected)]


async def test_callback_rejects_a_state_mismatch(app: FastAPI, client: httpx.AsyncClient) -> None:
    provider = install_oidc(app, GOOGLE_ACCOUNT)
    await register_client(client, email=EMAIL)
    client.cookies.clear()
    state = await _start(client)

    response = await _callback(client, f"{state}-piresignature", code="code-1")

    assert response.status_code == 400
    assert response.json()["detail"] == "Session OAuth invalide ou expirée."
    assert provider.exchange_calls == []
    assert ACCESS_COOKIE not in client.cookies


async def test_callback_requires_the_state_cookie(app: FastAPI, client: httpx.AsyncClient) -> None:
    provider = install_oidc(app, GOOGLE_ACCOUNT)
    await register_client(client, email=EMAIL)
    state = await _start(client)
    client.cookies.clear()

    response = await _callback(client, state, code="code-1")

    assert response.status_code == 400
    assert response.json()["detail"] == "Session OAuth invalide ou expirée."
    assert provider.exchange_calls == []


async def test_callback_refuses_an_unknown_account(app: FastAPI, client: httpx.AsyncClient) -> None:
    install_oidc(
        app,
        OidcIdentity(subject="s", email="inconnu@example.com", email_verified=True, name=None),
    )
    await register_client(client, email=EMAIL)
    client.cookies.clear()
    state = await _start(client)

    response = await _callback(client, state, code="code-1")

    assert response.status_code == 403
    assert response.json()["detail"] == "Aucun compte n'est associé à cette adresse e-mail."
    assert ACCESS_COOKIE not in client.cookies


async def test_callback_requires_a_verified_google_email(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    install_oidc(app, OidcIdentity(subject="s", email=EMAIL, email_verified=False, name=None))
    await register_client(client, email=EMAIL)
    client.cookies.clear()
    state = await _start(client)

    response = await _callback(client, state, code="code-1")

    assert response.status_code == 403
    assert response.json()["detail"] == "Adresse e-mail Google non vérifiée."
    assert ACCESS_COOKIE not in client.cookies


async def test_callback_reports_a_provider_failure(app: FastAPI, client: httpx.AsyncClient) -> None:
    install_oidc(app, error=OidcProviderError("google est tombé"))
    await register_client(client, email=EMAIL)
    client.cookies.clear()
    state = await _start(client)

    response = await _callback(client, state, code="code-1")

    assert response.status_code == 502
    assert response.json()["detail"] == "Connexion Google impossible."
    assert ACCESS_COOKIE not in client.cookies


async def test_callback_reports_a_cancelled_flow(app: FastAPI, client: httpx.AsyncClient) -> None:
    provider = install_oidc(app, GOOGLE_ACCOUNT)
    state = await _start(client)

    response = await _callback(client, state, error="access_denied")

    assert response.status_code == 400
    assert response.json()["detail"] == "Connexion Google annulée."
    assert provider.exchange_calls == []


async def test_callback_requires_a_code(app: FastAPI, client: httpx.AsyncClient) -> None:
    provider = install_oidc(app, GOOGLE_ACCOUNT)
    state = await _start(client)

    response = await _callback(client, state)

    assert response.status_code == 400
    assert response.json()["detail"] == "Session OAuth invalide ou expirée."
    assert provider.exchange_calls == []


async def test_callback_keeps_the_two_factor_challenge_when_totp_is_enabled(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    install_oidc(app, GOOGLE_ACCOUNT)
    await register_client(client, email=EMAIL)
    csrf = client.cookies.get(CSRF_COOKIE, "")
    setup = await client.post(
        f"{API_PREFIX}/auth/2fa/enable",
        json={"current_password": PASSWORD},
        headers={"x-csrf-token": csrf},
    )
    assert setup.status_code == 200, setup.text
    client.cookies.clear()
    state = await _start(client)

    response = await _callback(client, state, code="code-1")

    assert response.status_code == 200
    assert response.json()["totp_required"] is True
    assert response.json()["user"] is None
    assert TWO_FACTOR_COOKIE in client.cookies
    assert ACCESS_COOKIE not in client.cookies
    assert REFRESH_COOKIE not in client.cookies


def test_google_authorization_url_carries_state_and_redirect_uri() -> None:
    provider = GoogleOidcProvider(client_id="client", client_secret="secret")
    redirect_uri = "https://mirador.test/api/v1/auth/google/callback"

    url = provider.authorization_url(state="etat-1", redirect_uri=redirect_uri)

    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    assert (parsed.scheme, parsed.netloc) == ("https", "accounts.google.com")
    assert query["client_id"] == ["client"]
    assert query["response_type"] == ["code"]
    assert query["state"] == ["etat-1"]
    assert query["redirect_uri"] == [redirect_uri]
    assert "openid" in query["scope"][0] and "email" in query["scope"][0]


async def test_google_exchange_returns_the_verified_identity() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            assert "code=code-1" in (request.content.decode() or "")
            return httpx.Response(200, json={"access_token": "jeton-google", "expires_in": 3600})
        assert request.headers["authorization"] == "Bearer jeton-google"
        return httpx.Response(
            200,
            json={
                "sub": "1042",
                "email": "Ada@Example.com",
                "email_verified": True,
                "name": "Ada",
            },
        )

    provider = GoogleOidcProvider(
        client_id="client", client_secret="secret", transport=httpx.MockTransport(handler)
    )

    identity = await provider.exchange_code(code="code-1", redirect_uri="https://mirador.test/cb")

    assert identity == OidcIdentity(
        subject="1042", email="Ada@Example.com", email_verified=True, name="Ada"
    )


async def test_google_exchange_raises_when_google_refuses_the_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    provider = GoogleOidcProvider(
        client_id="client", client_secret="secret", transport=httpx.MockTransport(handler)
    )

    with pytest.raises(OidcProviderError):
        await provider.exchange_code(code="code-eteint", redirect_uri="https://mirador.test/cb")


async def test_google_exchange_requires_an_email() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "jeton-google"})
        return httpx.Response(200, json={"sub": "1042"})

    provider = GoogleOidcProvider(
        client_id="client", client_secret="secret", transport=httpx.MockTransport(handler)
    )

    with pytest.raises(OidcProviderError):
        await provider.exchange_code(code="code-1", redirect_uri="https://mirador.test/cb")


def test_google_provider_needs_a_client_id() -> None:
    """L'identifiant client est obligatoire : une valeur vide est un refus explicite."""
    with pytest.raises(ValueError, match="client_id"):
        GoogleOidcProvider(client_id="", client_secret="secret")
