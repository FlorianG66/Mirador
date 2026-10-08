"""Routes A2F : vérification d'un défi de connexion, activation et désactivation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import TWO_FACTOR_COOKIE
from app.core.cookies import clear_two_factor_cookie, set_auth_cookies
from app.core.deps import get_current_user, get_request_settings, get_session
from app.core.rate_limit import (
    TWO_FACTOR_VERIFY_RATE_LIMIT,
    TWO_FACTOR_VERIFY_RATE_WINDOW_SECONDS,
    rate_limit,
)
from app.core.security import hash_token
from app.models.user import User
from app.repositories import challenges as challenges_repository
from app.schemas.auth import LoginResponse, UserOut
from app.schemas.two_factor import (
    DisableTwoFactorRequest,
    EnableTwoFactorRequest,
    TOTPSetupResponse,
    TwoFactorVerifyRequest,
)
from app.services import sessions as sessions_service
from app.services import two_factor as two_factor_service

router = APIRouter(prefix="/auth/2fa")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
TwoFactorVerifyRateLimit = Annotated[
    None,
    Depends(
        rate_limit(
            "verify-2fa",
            limit=TWO_FACTOR_VERIFY_RATE_LIMIT,
            window_seconds=TWO_FACTOR_VERIFY_RATE_WINDOW_SECONDS,
        )
    ),
]


@router.post("/verify", response_model=LoginResponse)
async def verify(
    payload: TwoFactorVerifyRequest,
    request: Request,
    response: Response,
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_request_settings)],
    _rate: TwoFactorVerifyRateLimit,
) -> LoginResponse:
    """Échange le défi (cookie `mirador_2fa`) contre une session complète.

    Le défi est à usage unique : il est consommé, que le code soit un TOTP ou un
    code de secours (les codes de secours sont aussi consommés à l'usage).
    """
    token = request.cookies.get(TWO_FACTOR_COOKIE)
    challenge = (
        await challenges_repository.get_by_token_hash(session, hash_token(token)) if token else None
    )
    now = datetime.now(UTC)
    if challenge is None or challenge.used_at is not None or challenge.expires_at <= now:
        raise HTTPException(401, "Défi d'authentification invalide ou expiré.")
    user = await session.get(User, challenge.user_id)
    if user is None:
        raise HTTPException(401, "Compte introuvable.")
    totp_ok = two_factor_service.accepts_totp(user, payload.code)
    backup_ok = await two_factor_service.consume_backup_code(
        session, code_hash=hash_token(payload.code)
    )
    if not (totp_ok or backup_ok):
        raise HTTPException(401, "Code invalide.")
    await challenges_repository.mark_used(session, challenge)
    issued = await sessions_service.issue_session(session, user_id=user.id)
    set_auth_cookies(response, issued, settings)
    clear_two_factor_cookie(response, settings)
    return LoginResponse(user=UserOut(id=user.id, email=user.email))


@router.post("/enable", response_model=TOTPSetupResponse)
async def enable(
    payload: EnableTwoFactorRequest,
    current_user: CurrentUser,
    session: SessionDependency,
) -> TOTPSetupResponse:
    """Active (ou réactive) le TOTP : le secret et les codes sont montrés une fois."""
    try:
        setup = await two_factor_service.enable(
            session, user=current_user, current_password=payload.current_password
        )
    except two_factor_service.WrongCurrentPassword:
        raise HTTPException(401, "Mot de passe incorrect.") from None
    return TOTPSetupResponse(
        secret=setup.secret,
        otpauth_url=setup.otpauth_url,
        backup_codes=setup.backup_codes,
    )


@router.post("/disable", status_code=204)
async def disable(
    payload: DisableTwoFactorRequest,
    current_user: CurrentUser,
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> Response:
    """Désactive le TOTP et révoque les codes de secours restants."""
    try:
        await two_factor_service.disable(
            session, user=current_user, current_password=payload.current_password
        )
    except two_factor_service.WrongCurrentPassword:
        raise HTTPException(401, "Mot de passe incorrect.") from None
    response = Response(status_code=204)
    clear_two_factor_cookie(response, settings)
    return response
