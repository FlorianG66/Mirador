"""Routes d'authentification : inscription, connexion, rotation, déconnexion, profil."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import REFRESH_COOKIE, TWO_FACTOR_CHALLENGE_TTL_SECONDS
from app.core.cookies import clear_auth_cookies, set_auth_cookies, set_two_factor_cookie
from app.core.deps import (
    get_current_session,
    get_current_user,
    get_request_settings,
    get_session,
)
from app.core.rate_limit import (
    LOGIN_RATE_LIMIT,
    LOGIN_RATE_WINDOW_SECONDS,
    REGISTER_RATE_LIMIT,
    REGISTER_RATE_WINDOW_SECONDS,
    rate_limit,
)
from app.core.security import generate_token, hash_token
from app.models.enums import Role
from app.models.session import UserSession
from app.models.user import User
from app.repositories import challenges as challenges_repository
from app.repositories import memberships as memberships_repository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MembershipOut,
    MeResponse,
    OrganizationOut,
    RegisterRequest,
    RegisterResponse,
    UserOut,
)
from app.services import auth as auth_service
from app.services import sessions as sessions_service

router = APIRouter(prefix="/auth")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentSession = Annotated[UserSession, Depends(get_current_session)]
LoginRateLimit = Annotated[
    None,
    Depends(rate_limit("login", limit=LOGIN_RATE_LIMIT, window_seconds=LOGIN_RATE_WINDOW_SECONDS)),
]
RegisterRateLimit = Annotated[
    None,
    Depends(
        rate_limit(
            "register", limit=REGISTER_RATE_LIMIT, window_seconds=REGISTER_RATE_WINDOW_SECONDS
        )
    ),
]


@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register(
    payload: RegisterRequest,
    response: Response,
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_request_settings)],
    _rate: RegisterRateLimit,
) -> RegisterResponse:
    """Inscription : crée le compte, son organisation et le rattachement admin."""
    try:
        user, organization = await auth_service.register(
            session,
            email=payload.email,
            password=payload.password,
            organization_name=payload.organization_name,
            siren=payload.siren,
        )
    except auth_service.EmailAlreadyUsed:
        raise HTTPException(409, "Un compte existe déjà avec cet e-mail.") from None
    issued = await sessions_service.issue_session(session, user_id=user.id)
    set_auth_cookies(response, issued, settings)
    return RegisterResponse(
        user=UserOut(id=user.id, email=user.email),
        organization=OrganizationOut(id=organization.id, name=organization.name),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_request_settings)],
    _rate: LoginRateLimit,
) -> LoginResponse:
    """Connexion : réponse unique sur l'échec, puis session ou défi A2F.

    Quand le TOTP est actif, aucun cookie de session n'est posé : un défi de
    5 minutes est distribué et devra être échangé contre une session dans
    `/auth/2fa/verify`.
    """
    user = await auth_service.authenticate(session, email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(401, "Identifiants incorrects.")
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


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> dict[str, str]:
    """Tourne les jetons d'accès et de rafraîchissement (rotation à chaque usage)."""
    token = request.cookies.get(REFRESH_COOKIE)
    issued = await sessions_service.rotate_session(session, refresh_token=token) if token else None
    if issued is None:
        raise HTTPException(401, "Session expirée ou invalide.")
    set_auth_cookies(response, issued, settings)
    return {"status": "ok"}


@router.post("/logout", status_code=204)
async def logout(
    session: SessionDependency,
    current_session: CurrentSession,
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> Response:
    """Révoque la session côté base puis efface les cookies."""
    await sessions_service.revoke_session(session, row=current_session)
    response = Response(status_code=204)
    clear_auth_cookies(response, settings)
    return response


@router.get("/me", response_model=MeResponse)
async def me(
    current_user: CurrentUser,
    session: SessionDependency,
) -> MeResponse:
    """Utilisateur courant et ses organisations (tenant utilisateur déjà posé)."""
    rows = await memberships_repository.list_memberships_for_user(session, user_id=current_user.id)
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        memberships=[
            MembershipOut(organization_id=row.organization_id, role=Role(row.role)) for row in rows
        ],
    )
