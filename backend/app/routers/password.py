"""Routes de récupération de mot de passe : jeton à usage unique (phase 2c)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import get_request_settings, get_session
from app.core.rate_limit import (
    PASSWORD_FORGOT_RATE_LIMIT,
    PASSWORD_FORGOT_RATE_WINDOW_SECONDS,
    PASSWORD_RESET_RATE_LIMIT,
    PASSWORD_RESET_RATE_WINDOW_SECONDS,
    rate_limit,
)
from app.schemas.password import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
)
from app.services import password_reset as password_reset_service
from app.services.emails import EmailSender

router = APIRouter(prefix="/auth/password")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
ForgotRateLimit = Annotated[
    None,
    Depends(
        rate_limit(
            "forgot",
            limit=PASSWORD_FORGOT_RATE_LIMIT,
            window_seconds=PASSWORD_FORGOT_RATE_WINDOW_SECONDS,
        )
    ),
]
ResetRateLimit = Annotated[
    None,
    Depends(
        rate_limit(
            "reset",
            limit=PASSWORD_RESET_RATE_LIMIT,
            window_seconds=PASSWORD_RESET_RATE_WINDOW_SECONDS,
        )
    ),
]


@router.post("/forgot", response_model=ForgotPasswordResponse)
async def forgot(
    payload: ForgotPasswordRequest,
    request: Request,
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_request_settings)],
    _rate: ForgotRateLimit,
) -> ForgotPasswordResponse:
    """Émet un lien de réinitialisation si le compte existe ; réponse toujours pareille."""
    sender: EmailSender = request.app.state.email_sender
    await password_reset_service.request_reset(
        session,
        email=payload.email,
        base_url=settings.app_base_url,
        sender=sender,
    )
    return ForgotPasswordResponse()


@router.post("/reset")
async def reset(
    payload: ResetPasswordRequest,
    session: SessionDependency,
    _rate: ResetRateLimit,
) -> dict[str, str]:
    """Réinitialise le mot de passe et révoque toutes les sessions du compte."""
    if not await password_reset_service.reset_password(
        session, token=payload.token, new_password=payload.new_password
    ):
        raise HTTPException(401, "Lien de réinitialisation invalide ou expiré.")
    return {"status": "ok"}
