"""Routes du mode démo (SPEC §9) : scénarios publics, session et liens à durée limitée."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.cookies import set_auth_cookies
from app.core.deps import get_current_user, get_request_settings, get_session
from app.core.permissions import require_admin
from app.core.rate_limit import (
    DEMO_LINK_CREATE_RATE_LIMIT,
    DEMO_LINK_CREATE_RATE_WINDOW_SECONDS,
    DEMO_LINK_RATE_LIMIT,
    DEMO_LINK_RATE_WINDOW_SECONDS,
    DEMO_SESSION_RATE_LIMIT,
    DEMO_SESSION_RATE_WINDOW_SECONDS,
    rate_limit,
)
from app.models.membership import Membership
from app.models.user import User
from app.repositories import organizations as organizations_repository
from app.schemas.auth import OrganizationOut, UserOut
from app.schemas.demo import (
    DemoLinkOut,
    DemoLinkRequest,
    DemoScenarioOut,
    DemoSessionRequest,
    DemoSessionResponse,
)
from app.services import demo as demo_service
from app.services import sessions as sessions_service
from app.services.errors import ServiceProblem

# Routes publiques : `/demo` (scénarios, ouverture d'une session, lien).
router = APIRouter(prefix="/demo")
# Route d'administration : le dirigeant génère un lien pour un prospect depuis son
# organisation (même préfixe que les autres ressources d'organisation).
organizations_router = APIRouter(prefix="/organizations/{organization_id}")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminMembership = Annotated[Membership, Depends(require_admin)]
SettingsDependency = Annotated[Settings, Depends(get_request_settings)]

DemoSessionRateLimit = Annotated[
    None,
    Depends(
        rate_limit(
            "demo_session",
            limit=DEMO_SESSION_RATE_LIMIT,
            window_seconds=DEMO_SESSION_RATE_WINDOW_SECONDS,
        )
    ),
]
DemoLinkRateLimit = Annotated[
    None,
    Depends(
        rate_limit(
            "demo_link",
            limit=DEMO_LINK_RATE_LIMIT,
            window_seconds=DEMO_LINK_RATE_WINDOW_SECONDS,
        )
    ),
]
DemoLinkCreateRateLimit = Annotated[
    None,
    Depends(
        rate_limit(
            "demo_link_create",
            limit=DEMO_LINK_CREATE_RATE_LIMIT,
            window_seconds=DEMO_LINK_CREATE_RATE_WINDOW_SECONDS,
        )
    ),
]


@router.get("/scenarios", response_model=list[DemoScenarioOut])
async def list_demo_scenarios() -> list[DemoScenarioOut]:
    """Liste des scénarios sectoriels disponibles pour la démo publique."""
    return [
        DemoScenarioOut(key=scenario.sector, organization_name=scenario.organization_name)
        for scenario in demo_service.list_scenarios()
    ]


@router.post("/sessions", status_code=201, response_model=DemoSessionResponse)
async def create_demo_session(
    payload: DemoSessionRequest,
    response: Response,
    session: SessionDependency,
    settings: SettingsDependency,
    _rate: DemoSessionRateLimit,
) -> DemoSessionResponse:
    """Ouvre une session de démonstration isolée (entreprise fictive, données mock)."""
    user, organization, expires_at = await demo_service.create_demo_session(
        session, sector=payload.sector, ttl_minutes=settings.demo_session_ttl_minutes
    )
    issued = await sessions_service.issue_session(session, user_id=user.id)
    set_auth_cookies(response, issued, settings)
    return DemoSessionResponse(
        user=UserOut(id=user.id, email=user.email),
        organization=OrganizationOut(id=organization.id, name=organization.name, is_demo=True),
        sector=payload.sector,
        expires_at=expires_at,
    )


@router.post("/links/{token}", status_code=201, response_model=DemoSessionResponse)
async def redeem_demo_link(
    token: str,
    response: Response,
    session: SessionDependency,
    settings: SettingsDependency,
    _rate: DemoLinkRateLimit,
) -> DemoSessionResponse:
    """Échange un lien `/demo/<token>` contre une session de démonstration."""
    sector = await demo_service.redeem_demo_link(session, token=token)
    user, organization, expires_at = await demo_service.create_demo_session(
        session, sector=sector, ttl_minutes=settings.demo_session_ttl_minutes
    )
    issued = await sessions_service.issue_session(session, user_id=user.id)
    set_auth_cookies(response, issued, settings)
    return DemoSessionResponse(
        user=UserOut(id=user.id, email=user.email),
        organization=OrganizationOut(id=organization.id, name=organization.name, is_demo=True),
        sector=sector,
        expires_at=expires_at,
    )


@organizations_router.post(
    "/demo-links",
    status_code=201,
    response_model=DemoLinkOut,
)
async def create_demo_link(
    organization_id: uuid.UUID,
    payload: DemoLinkRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    _current_user: CurrentUser,
    membership: AdminMembership,
    _rate: DemoLinkCreateRateLimit,
) -> DemoLinkOut:
    """Génère un lien de démonstration à destination d'un prospect (réservé aux admins)."""
    organization = await organizations_repository.get_organization(session, organization_id)
    if organization is None:
        raise ServiceProblem(404, "Organisation introuvable.")
    if organization.is_demo:
        raise ServiceProblem(403, "Une organisation de démonstration ne peut pas générer de liens.")
    token, expires_at = await demo_service.create_demo_link(
        session,
        sector=payload.sector,
        organization_id=membership.organization_id,
        created_by_user_id=_current_user.id,
        ttl_hours=settings.demo_link_ttl_hours,
    )
    path = f"/demo/{token}"
    base_url = settings.app_base_url.rstrip("/")
    return DemoLinkOut(
        token=token,
        path=path,
        url=f"{base_url}{path}",
        sector=payload.sector,
        expires_at=expires_at,
    )
