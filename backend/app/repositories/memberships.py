"""Repository : memberships (accès aux données uniquement, aucune règle métier)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Role
from app.models.membership import Membership
from app.models.organization import Organization


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


async def get_membership(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> Membership | None:
    """Rattachement d'un utilisateur à une organisation : filtre explicite + RLS."""
    result = await session.execute(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_membership(session: AsyncSession, membership: Membership) -> None:
    """Retire un rattachement ; ses permissions suivent en cascade (FK). Flush seulement."""
    await session.delete(membership)
    await session.flush()


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


async def list_memberships_with_organization_for_user(
    session: AsyncSession, *, user_id: uuid.UUID
) -> list[tuple[Membership, Organization]]:
    """Rattachements d'un utilisateur, avec l'organisation (nom et marqueur démo).

    L'UI a besoin du nom pour l'écran de choix d'organisation et du drapeau `is_demo`
    pour afficher le bandeau « Démo ». La jointure reste filtrée par utilisateur,
    donc lisible sous la politique RLS `USING` de `memberships`.
    """
    result = await session.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == user_id)
        .order_by(Membership.created_at, Membership.organization_id)
    )
    return [(membership, organization) for membership, organization in result.all()]
