"""Routes d'équipe : membres, permissions par module, révocation, journal d'audit."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.permissions import get_current_tenant, require_admin
from app.models.membership import Membership
from app.schemas.team import (
    AuditLogOut,
    MemberOut,
    MyPermissionsOut,
    PermissionsOut,
    UpdatePermissionsRequest,
)
from app.services import audit as audit_service
from app.services import team as team_service

router = APIRouter(prefix="/organizations/{organization_id}")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentTenant = Annotated[Membership, Depends(get_current_tenant)]
AdminMembership = Annotated[Membership, Depends(require_admin)]


@router.get("/members", response_model=list[MemberOut])
async def list_team(session: SessionDependency, membership: CurrentTenant) -> list[MemberOut]:
    """Membres de l'organisation avec leurs niveaux effectifs (membre inclus)."""
    return await team_service.list_members(session, organization_id=membership.organization_id)


@router.get("/permissions", response_model=MyPermissionsOut)
async def my_permissions(session: SessionDependency, membership: CurrentTenant) -> MyPermissionsOut:
    """Mes niveaux par module : le frontend s'en sert pour ses gardes de routes."""
    return await team_service.my_permissions(session, membership=membership)


@router.patch("/members/{user_id}/permissions", response_model=PermissionsOut)
async def update_member_permissions(
    user_id: uuid.UUID,
    payload: UpdatePermissionsRequest,
    session: SessionDependency,
    membership: AdminMembership,
) -> PermissionsOut:
    """Remplace les modules visibles d'un membre ; l'avant/après est journalisé."""
    return await team_service.update_permissions(
        session, actor=membership, target_user_id=user_id, modules=payload.modules
    )


@router.delete("/members/{user_id}", status_code=204)
async def revoke_member(
    user_id: uuid.UUID,
    session: SessionDependency,
    membership: AdminMembership,
) -> Response:
    """Révoque l'accès d'un membre ; ses permissions tombent en cascade (admin)."""
    await team_service.revoke_member(session, actor=membership, target_user_id=user_id)
    return Response(status_code=204)


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def list_audit_logs(
    session: SessionDependency, membership: AdminMembership
) -> list[AuditLogOut]:
    """Journal des actions sensibles de l'organisation (admin uniquement)."""
    return await audit_service.list_recent(session, organization_id=membership.organization_id)
