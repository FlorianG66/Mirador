"""Distribution des cookies d'authentification, partagée entre les routes.

Les attributs (httpOnly, Secure, SameSite, chemins) sont fixés en un seul endroit :
login, rotation, vérification A2F et déconnexion posent/effacent exactement les
mêmes cookies (AGENTS.md §5).
"""

from __future__ import annotations

from fastapi import Response

from app.core.config import Settings
from app.core.constants import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    TWO_FACTOR_COOKIE,
)
from app.core.security import ACCESS_TOKEN_TTL_SECONDS, REFRESH_TOKEN_TTL_SECONDS
from app.services.sessions import IssuedSession


def _secure(settings: Settings) -> bool:
    return settings.environment == "production"


def set_auth_cookies(response: Response, issued: IssuedSession, settings: Settings) -> None:
    """Distribue les trois cookies : accès et rafraîchissement cachés, CSRF lisible."""
    secure = _secure(settings)
    response.set_cookie(
        ACCESS_COOKIE,
        issued.access_token,
        max_age=ACCESS_TOKEN_TTL_SECONDS,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    # Le rafraîchissement ne quitte jamais la zone d'authentification.
    response.set_cookie(
        REFRESH_COOKIE,
        issued.refresh_token,
        max_age=REFRESH_TOKEN_TTL_SECONDS,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/v1/auth",
    )
    # Le CSRF doit être lisible par le frontend pour remplir l'en-tête.
    response.set_cookie(
        CSRF_COOKIE,
        issued.csrf_token,
        max_age=REFRESH_TOKEN_TTL_SECONDS,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    """Supprime les trois cookies d'authentification (mêmes attributs qu'à la pose)."""
    secure = _secure(settings)
    response.delete_cookie(ACCESS_COOKIE, path="/", secure=secure, samesite="lax")
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth", secure=secure, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=secure, samesite="lax")


def set_two_factor_cookie(
    response: Response, token: str, settings: Settings, *, max_age: int
) -> None:
    """Défi A2F : httpOnly, limité à la zone d'authentification, courte durée."""
    response.set_cookie(
        TWO_FACTOR_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        secure=_secure(settings),
        samesite="lax",
        path="/api/v1/auth",
    )


def clear_two_factor_cookie(response: Response, settings: Settings) -> None:
    """Efface le défi A2F (fin du parcours de vérification)."""
    response.delete_cookie(
        TWO_FACTOR_COOKIE, path="/api/v1/auth", secure=_secure(settings), samesite="lax"
    )
