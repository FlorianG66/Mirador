"""Routes d'authentification : inscription, connexion, rotation, déconnexion, profil."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE
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
from app.core.security import ACCESS_TOKEN_TTL_SECONDS, REFRESH_TOKEN_TTL_SECONDS
from app.models.enums import Role
from app.models.session import UserSession
from app.models.user import User
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
from app.services.sessions import IssuedSession

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


def _set_auth_cookies(response: Response, issued: IssuedSession, settings: Settings) -> None:
    """Distribue les trois cookies : accès et rafraîchissement cachés, CSRF lisible."""
    secure = settings.environment == "production"
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


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    """Supprime les trois cookies (mêmes attributs que lors de la pose)."""
    secure = settings.environment == "production"
    response.delete_cookie(ACCESS_COOKIE, path="/", secure=secure, samesite="lax")
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth", secure=secure, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=secure, samesite="lax")


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
    _set_auth_cookies(response, issued, settings)
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
    """Connexion e-mail/mot de passe : un message unique, quel que soit l'échec."""
    user = await auth_service.authenticate(session, email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(401, "Identifiants incorrects.")
    issued = await sessions_service.issue_session(session, user_id=user.id)
    _set_auth_cookies(response, issued, settings)
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
    _set_auth_cookies(response, issued, settings)
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
    _clear_auth_cookies(response, settings)
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
