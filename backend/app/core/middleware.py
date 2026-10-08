"""Middleware transverse : en-têtes de sécurité et protection CSRF.

Le CSRF est du double submit : le jeton livré dans un cookie lisible doit être
repris dans l'en-tête `X-CSRF-Token`. Un site tiers peut forcer le navigateur à
envoyer le cookie, mais pas à lire sa valeur pour remplir l'en-tête.
"""

from __future__ import annotations

import hmac
from http import HTTPStatus
from http.cookies import SimpleCookie

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.constants import ACCESS_COOKIE, API_PREFIX, CSRF_COOKIE, CSRF_HEADER, REFRESH_COOKIE

# Les méthodes sans effet : ni écriture, donc pas d'exposition CSRF.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
# Ces routes sont le point d'entrée du jeton CSRF : elles en délivrent un, on ne
# peut pas en exiger une au moment de la première connexion.
CSRF_EXEMPT_PATHS = frozenset({f"{API_PREFIX}/auth/register", f"{API_PREFIX}/auth/login"})


def _security_headers(settings: Settings) -> list[tuple[bytes, bytes]]:
    """En-têtes de sécurité présents sur toutes les réponses (y compris les erreurs)."""
    headers = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"same-origin"),
        (b"cross-origin-opener-policy", b"same-origin"),
    ]
    if settings.environment == "production":
        headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
    return headers


def _cookies_from_scope(scope: Scope) -> SimpleCookie:
    """Décode l'en-tête Cookie de la requête (jamais de cookie → jar vide)."""
    jar: SimpleCookie = SimpleCookie()
    for name, value in scope.get("headers", ()):
        if name == b"cookie":
            jar.load(value.decode("latin-1"))
    return jar


def _auth_cookies_present(scope: Scope) -> bool:
    """Un des deux cookies d'authentification est joint à la requête."""
    jar = _cookies_from_scope(scope)
    return ACCESS_COOKIE in jar or REFRESH_COOKIE in jar


def _csrf_is_valid(scope: Scope) -> bool:
    """Cookie et en-tête CSRF présents, non vidents et identiques (comparaison constante)."""
    provided = None
    for name, value in scope.get("headers", ()):
        if name == CSRF_HEADER.encode():
            provided = value.decode("latin-1")
    cookie = _cookies_from_scope(scope).get(CSRF_COOKIE)
    if provided is None or cookie is None or not provided or not cookie.value:
        return False
    return hmac.compare_digest(provided, cookie.value)


class SecurityMiddleware:
    """Ajoute les en-têtes de sécurité et refuse les écritures sans jeton CSRF."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        method = scope["method"]
        if (
            method not in SAFE_METHODS
            and path.startswith(API_PREFIX)
            and path not in CSRF_EXEMPT_PATHS
            # Sans cookie d'authentification, il n'y a pas de credentiel ambiant
            # à exploiter : la CSRF ne s'applique pas (un 405 reste un 405).
            and _auth_cookies_present(scope)
            and not _csrf_is_valid(scope)
        ):
            response = JSONResponse(
                status_code=HTTPStatus.FORBIDDEN,
                content={
                    "type": "about:blank",
                    "title": "Forbidden",
                    "status": 403,
                    "detail": "Jeton CSRF manquant ou invalide.",
                    "instance": path,
                },
                media_type="application/problem+json",
                headers={"x-frame-options": "DENY"},
            )
            await response(scope, receive, self._send_with_headers(send))
            return
        await self.app(scope, receive, self._send_with_headers(send))

    def _send_with_headers(self, send: Send) -> Send:
        """Passe la main en ajoutant les en-têtes de sécurité au démarrage de réponse."""

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.extend(_security_headers(self.settings))
            await send(message)

        return send_with_headers
