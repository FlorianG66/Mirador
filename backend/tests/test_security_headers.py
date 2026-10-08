"""En-têtes de sécurité et attributs Secure des cookies en production."""

from __future__ import annotations

import httpx
from starlette.types import Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.constants import ACCESS_COOKIE, API_PREFIX
from app.core.middleware import SecurityMiddleware
from app.main import create_app
from tests.conftest import register_client

EXPECTED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "same-origin",
    "cross-origin-opener-policy": "same-origin",
}


async def test_websocket_scope_bypasses_the_security_middleware() -> None:
    """La couverture n'a de sens que sur HTTP : un websocket passe tel quel."""
    seen: list[Scope] = []

    async def passthrough(scope: Scope, receive: Receive, send: Send) -> None:
        del receive, send
        seen.append(scope)

    middleware = SecurityMiddleware(passthrough, Settings())

    async def silence(message: Message) -> None:
        del message

    scope: Scope = {"type": "websocket", "path": "/", "headers": []}
    await middleware(scope, silence, silence)

    assert seen == [scope]


async def test_a_success_response_carries_the_security_headers(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{API_PREFIX}/health")

    for name, value in EXPECTED_HEADERS.items():
        assert response.headers[name] == value


async def test_an_error_response_carries_the_security_headers(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{API_PREFIX}/inexistant")

    assert response.status_code == 404
    for name, value in EXPECTED_HEADERS.items():
        assert response.headers[name] == value


async def test_cookies_are_secure_in_production(migrated_test_database_url: str) -> None:
    app = create_app(Settings(database_url=migrated_test_database_url, environment="production"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await register_client(client)
        assert response.cookies.get(ACCESS_COOKIE), "cookie d'accès absent"
        cookies = response.headers.get_list("set-cookie")
        access = next(h for h in cookies if h.startswith(f"{ACCESS_COOKIE}="))
        assert "Secure" in access
        await app.state.engine.dispose()
