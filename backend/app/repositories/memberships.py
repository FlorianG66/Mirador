"""Repository : memberships (accès aux données uniquement, aucune règle métier)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Role
from app.models.membership import Membership


async def create_membership(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    role: Role,
) -> Membership:
    """Rattache un utilisateur à une organisation avec un rôle. Flush seulement."""
    membership = Membership(organization_id=organization_id, user_id=user_id, role=role)
    session.add(membership)
    await session.flush()
    return membership


async def list_members(session: AsyncSession, *, organization_id: uuid.UUID) -> list[Membership]:
    """Membres d'une organisation : filtre explicite + RLS (défense en profondeur)."""
    result = await session.execute(
        select(Membership)
        .where(Membership.organization_id == organization_id)
        .order_by(Membership.created_at, Membership.user_id)
    )
    return list(result.scalars().all())


async def list_memberships_for_user(
    session: AsyncSession, *, user_id: uuid.UUID
) -> list[Membership]:
    """Organisations d'un utilisateur : lisible avant de connaître l'organisation active."""
    result = await session.execute(
        select(Membership)
        .where(Membership.user_id == user_id)
        .order_by(Membership.created_at, Membership.organization_id)
    )
    return list(result.scalars().all())
