"""Routes d'invitation : émission, liste, révocation (admin), acceptation (invité)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import get_current_user, get_request_settings, get_session
from app.core.permissions import require_admin
from app.core.rate_limit import (
    INVITE_RATE_LIMIT,
    INVITE_RATE_WINDOW_SECONDS,
    rate_limit,
)
from app.models.membership import Membership
from app.models.user import User
from app.schemas.invitations import (
    AcceptInvitationRequest,
    AcceptInvitationResponse,
    InvitationCreateRequest,
    InvitationOut,
)
from app.services import invitations as invitations_service
from app.services.emails import EmailSender

router = APIRouter(prefix="/organizations/{organization_id}/invitations")
accept_router = APIRouter(prefix="/auth/invitations")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminMembership = Annotated[Membership, Depends(require_admin)]
InviteRateLimit = Annotated[
    None,
    Depends(
        rate_limit(
            "invite",
            limit=INVITE_RATE_LIMIT,
            window_seconds=INVITE_RATE_WINDOW_SECONDS,
        )
    ),
]


@router.post("", status_code=201, response_model=InvitationOut)
async def create_invitation(
    payload: InvitationCreateRequest,
    session: SessionDependency,
    membership: AdminMembership,
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_request_settings)],
    request: Request,
    _rate: InviteRateLimit,
) -> InvitationOut:
    """Invite un collaborateur par e-mail avec ses modules (admin uniquement)."""
    sender: EmailSender = request.app.state.email_sender
    return await invitations_service.invite(
        session,
        organization_id=membership.organization_id,
        actor=user,
        email=payload.email,
        role=payload.role,
        modules=payload.modules,
        base_url=settings.app_base_url,
        sender=sender,
    )


@router.get("", response_model=list[InvitationOut])
async def list_invitations(
    session: SessionDependency, membership: AdminMembership
) -> list[InvitationOut]:
    """Invitations en attente de l'organisation (admin uniquement)."""
    return await invitations_service.list_pending(
        session, organization_id=membership.organization_id
    )


@router.delete("/{invitation_id}", status_code=204)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    session: SessionDependency,
    membership: AdminMembership,
) -> Response:
    """Annule une invitation : son jeton ne vaut plus rien (admin uniquement)."""
    await invitations_service.revoke(
        session,
        organization_id=membership.organization_id,
        invitation_id=invitation_id,
    )
    return Response(status_code=204)


@accept_router.post("/accept", status_code=201, response_model=AcceptInvitationResponse)
async def accept_invitation(
    payload: AcceptInvitationRequest,
    session: SessionDependency,
    user: CurrentUser,
) -> AcceptInvitationResponse:
    """Consomme le lien : crée le rattachement et les permissions choisies."""
    return await invitations_service.accept(
        session, user=user, token=payload.token, organization_id=payload.organization_id
    )
