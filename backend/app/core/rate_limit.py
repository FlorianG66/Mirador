"""Rate limiting en mémoire sur les routes d'authentification (phase 2b).

Une fenêtre glissante par couple (route, IP) : simple, sans dépendance, correct
tant qu'un seul processus sert l'API (voir docs/DECISIONS.md — un répartiteur ou
plusieurs processus devront partager un compteur externe avant la montée en charge).
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request

# Fenêtre glissante par couple (route, IP).
LOGIN_RATE_LIMIT = 5
LOGIN_RATE_WINDOW_SECONDS = 60
REGISTER_RATE_LIMIT = 5
REGISTER_RATE_WINDOW_SECONDS = 60

# Second facteur et récupération de compte (phase 2c) : quotas volontairement stricts.
TWO_FACTOR_VERIFY_RATE_LIMIT = 5
TWO_FACTOR_VERIFY_RATE_WINDOW_SECONDS = 60
PASSWORD_FORGOT_RATE_LIMIT = 3
PASSWORD_FORGOT_RATE_WINDOW_SECONDS = 15 * 60
PASSWORD_RESET_RATE_LIMIT = 5
PASSWORD_RESET_RATE_WINDOW_SECONDS = 60 * 60

# Invitation d'un collaborateur (phase 2d) : chaque tentative déclenche un e-mail.
INVITE_RATE_LIMIT = 10
INVITE_RATE_WINDOW_SECONDS = 60 * 60

# Connexion Google (phase 2e) : démarrage et callback partagent le même quota.
GOOGLE_RATE_LIMIT = 10
GOOGLE_RATE_WINDOW_SECONDS = 60

# Démonstration publique (phase 7) : chaque ouverture crée une organisation et
# seme ses données. Le quota est volontairement bas (SPEC §9 : rate limiting
# renforcé) ; l'échange d'un lien est un peu plus permissif (ouverture répétée).
DEMO_SESSION_RATE_LIMIT = 5
DEMO_SESSION_RATE_WINDOW_SECONDS = 10 * 60
DEMO_LINK_RATE_LIMIT = 10
DEMO_LINK_RATE_WINDOW_SECONDS = 10 * 60
DEMO_LINK_CREATE_RATE_LIMIT = 20
DEMO_LINK_CREATE_RATE_WINDOW_SECONDS = 60 * 60

# Démarrage d'une démonstration (phase 7) : chaque appel crée (une seule fois) une
# organisation et une session. Quota renforcé (SPEC §9) : 5 par heure et par IP.
DEMO_START_RATE_LIMIT = 5
DEMO_START_RATE_WINDOW_SECONDS = 60 * 60


class RateLimiter:
    """Compteur de tentatives par clé, purge automatique des fenêtres expirées."""

    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, *, limit: int, window_seconds: float) -> int:
        """Enregistre une tentative ; retourne 0, ou le Retry-After en secondes."""
        now = time.monotonic()
        attempts = [moment for moment in self._attempts[key] if moment > now - window_seconds]
        self._attempts[key] = attempts
        if len(attempts) >= limit:
            return max(1, int(attempts[0] + window_seconds - now) + 1)
        attempts.append(now)
        return 0


def rate_limit(
    name: str, *, limit: int, window_seconds: int
) -> Callable[[Request], Awaitable[None]]:
    """Dépendance FastAPI : 429 + Retry-After au-delà du quota de la route."""

    async def dependency(request: Request) -> None:
        limiter: RateLimiter = request.app.state.rate_limiter
        client = request.client
        key = f"{name}:{client.host if client is not None else 'unknown'}"
        retry_after = limiter.check(key, limit=limit, window_seconds=window_seconds)
        if retry_after:
            raise HTTPException(
                429,
                "Trop de tentatives. Réessayez dans quelques instants.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
