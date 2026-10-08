"""Service équipe : membres, permissions par module, révocation (SPEC §2).

Toute modification de permission est journalisée : le journal d'audit conserve
l'état avant/après de chaque changement (AGENTS §5).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import modules_for, modules_to_plain
from app.models.enums import Module, PermissionLevel, Role
from app.models.membership import Membership
from app.models.user import User
from app.repositories import memberships as memberships_repository
from app.repositories import module_permissions as module_permissions_repository
from app.schemas.team import MemberOut, MyPermissionsOut, PermissionsOut
from app.services import audit as audit_service
from app.services.errors import ServiceProblem


async def _stored_modules(
    session: AsyncSession, membership_id: uuid.UUID
) -> dict[Module, PermissionLevel]:
    rows = await module_permissions_repository.list_for_membership(
        session, membership_id=membership_id
    )
    return {Module(row.module): PermissionLevel(row.level) for row in rows}


async def _effective_modules(
    session: AsyncSession, membership: Membership
) -> dict[Module, PermissionLevel]:
    """Niveaux affichables d'un membre : stocké, ou `edit` partout pour un admin."""
    return modules_for(membership.role, await _stored_modules(session, membership.id))


async def list_members(session: AsyncSession, *, organization_id: uuid.UUID) -> list[MemberOut]:
    """Équipe complète avec les niveaux effectifs de chaque membre."""
    members: list[MemberOut] = []
    for membership in await memberships_repository.list_members(
        session, organization_id=organization_id
    ):
        user = await session.get(User, membership.user_id)
        if user is None:
            continue  # la clé étrangère garantit l'existence ; garde pour le typage
        members.append(
            MemberOut(
                user_id=user.id,
                email=user.email,
                role=Role(membership.role),
                modules=await _effective_modules(session, membership),
            )
        )
    return members


async def my_permissions(session: AsyncSession, *, membership: Membership) -> MyPermissionsOut:
    """Niveaux du membre courant : sert aux gardes de routes côté frontend (phase 3)."""
    return MyPermissionsOut(
        role=Role(membership.role),
        modules=await _effective_modules(session, membership),
    )


async def update_permissions(
    session: AsyncSession,
    *,
    actor: Membership,
    target_user_id: uuid.UUID,
    modules: dict[Module, PermissionLevel],
) -> PermissionsOut:
    """Remplace les modules visibles d'un membre ; l'avant/après est journalisé."""
    target = await memberships_repository.get_membership(
        session, organization_id=actor.organization_id, user_id=target_user_id
    )
    if target is None:
        raise ServiceProblem(404, "Membre introuvable.")
    before = await _effective_modules(session, target)
    await module_permissions_repository.replace_for_membership(
        session,
        organization_id=actor.organization_id,
        membership_id=target.id,
        modules={module.value: level.value for module, level in modules.items()},
    )
    after = modules_for(target.role, modules)
    await audit_service.record(
        session,
        organization_id=actor.organization_id,
        actor_user_id=actor.user_id,
        action="membership.permissions.updated",
        resource_type="membership",
        resource_id=str(target_user_id),
        payload={
            "before": modules_to_plain(before),
            "after": modules_to_plain(after),
        },
    )
    return PermissionsOut(modules=after)


async def revoke_member(
    session: AsyncSession, *, actor: Membership, target_user_id: uuid.UUID
) -> None:
    """Retire un membre : permissions en cascade, accès perdu immédiatement (SPEC §2).

    Se révoquer soi-même est refusé : l'organisation conserve toujours un admin.
    """
    if target_user_id == actor.user_id:
        raise ServiceProblem(400, "Vous ne pouvez pas révoquer votre propre accès.")
    target = await memberships_repository.get_membership(
        session, organization_id=actor.organization_id, user_id=target_user_id
    )
    if target is None:
        raise ServiceProblem(404, "Membre introuvable.")
    target_user = await session.get(User, target_user_id)
    await audit_service.record(
        session,
        organization_id=actor.organization_id,
        actor_user_id=actor.user_id,
        action="membership.revoked",
        resource_type="membership",
        resource_id=str(target_user_id),
        payload={
            "email": target_user.email if target_user else None,
            "role": target.role,
        },
    )
    await memberships_repository.delete_membership(session, target)
