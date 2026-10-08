"""Connexion Google (OIDC) : démarrage du parcours et retour du fournisseur.

Deux routes en GET : `/auth/google` pose l'état puis redirige vers Google, et
`/auth/google/callback` vérifie l'état, échange le code et distribue la session
— ou relève le défi A2F quand le TOTP est actif. Aucun try/except ici : les
refus remontent en `ServiceProblem` / `OidcProviderError` (gestionnaires
centraux de `app.core.errors`).
"""

from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import OAUTH_STATE_COOKIE, TWO_FACTOR_CHALLENGE_TTL_SECONDS
from app.core.cookies import (
    clear_oauth_state_cookie,
    set_auth_cookies,
    set_oauth_state_cookie,
    set_two_factor_cookie,
)
from app.core.deps import get_request_settings, get_session
from app.core.rate_limit import GOOGLE_RATE_LIMIT, GOOGLE_RATE_WINDOW_SECONDS, rate_limit
from app.core.security import generate_token, hash_token
from app.repositories import challenges as challenges_repository
from app.schemas.auth import LoginResponse, UserOut
from app.services import auth as auth_service
from app.services import sessions as sessions_service
from app.services.oidc import OidcProvider

router = APIRouter(prefix="/auth/google")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
GoogleRateLimit = Annotated[
    None,
    Depends(
        rate_limit("google", limit=GOOGLE_RATE_LIMIT, window_seconds=GOOGLE_RATE_WINDOW_SECONDS)
    ),
]


def _provider(request: Request) -> OidcProvider:
    """Fournisseur Google ; 404 s'il n'est pas configuré (identifiants absents)."""
    provider: OidcProvider | None = request.app.state.oidc_provider
    if provider is None:
        raise HTTPException(404, "Connexion Google indisponible.")
    return provider


def _require_matching_state(request: Request) -> None:
    """Anti-CSRF : l'état du cookie doit être celui renvoyé par Google, à l'identique."""
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE, "")
    query_state = request.query_params.get("state", "")
    if not cookie_state or not query_state or not hmac.compare_digest(cookie_state, query_state):
        raise HTTPException(400, "Session OAuth invalide ou expirée.")


@router.get("", status_code=302)
async def start(
    request: Request,
    settings: Annotated[Settings, Depends(get_request_settings)],
    _rate: GoogleRateLimit,
) -> RedirectResponse:
    """Pose l'état dans un cookie httpOnly puis renvoie l'URL d'autorisation Google."""
    provider = _provider(request)
    state = generate_token()
    redirect = RedirectResponse(
        provider.authorization_url(state=state, redirect_uri=settings.google_redirect_uri),
        status_code=302,
    )
    set_oauth_state_cookie(redirect, state, settings)
    return redirect


@router.get("/callback", response_model=LoginResponse)
async def callback(
    request: Request,
    response: Response,
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_request_settings)],
    _rate: GoogleRateLimit,
) -> LoginResponse:
    """Valide l'état, échange le code puis ouvre la session (ou relève le défi A2F).

    Une erreur du fournisseur (`OidcProviderError`) remonte jusqu'au gestionnaire
    central : 502 à détail figé, le détail technique n'est que journalisé.
    """
    provider = _provider(request)
    _require_matching_state(request)
    if "error" in request.query_params:
        raise HTTPException(400, "Connexion Google annulée.")
    code = request.query_params.get("code", "")
    if not code:
        raise HTTPException(400, "Session OAuth invalide ou expirée.")
    identity = await provider.exchange_code(code=code, redirect_uri=settings.google_redirect_uri)
    user = await auth_service.authenticate_google(session, identity=identity)
    # L'état est consommé : le parcours ne peut pas être rejoué depuis ce navigateur.
    clear_oauth_state_cookie(response, settings)
    if user.totp_enabled_at is not None:
        token = generate_token()
        await challenges_repository.create_auth_challenge(
            session,
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(seconds=TWO_FACTOR_CHALLENGE_TTL_SECONDS),
        )
        set_two_factor_cookie(response, token, settings, max_age=TWO_FACTOR_CHALLENGE_TTL_SECONDS)
        return LoginResponse(totp_required=True)
    issued = await sessions_service.issue_session(session, user_id=user.id)
    set_auth_cookies(response, issued, settings)
    return LoginResponse(user=UserOut(id=user.id, email=user.email))
