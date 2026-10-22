"""Repository : organisations (accès aux données uniquement, aucune règle métier)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


async def create_organization(
    session: AsyncSession,
    *,
    name: str,
    siren: str | None = None,
    is_demo: bool = False,
    demo_sector: str | None = None,
    demo_expires_at: datetime | None = None,
) -> Organization:
    """Insère une organisation. Flush seulement : le commit appartient à la requête."""
    organization = Organization(
        name=name,
        siren=siren,
        is_demo=is_demo,
        demo_sector=demo_sector,
        demo_expires_at=demo_expires_at,
    )
    session.add(organization)
    await session.flush()
    return organization


async def get_organization(
    session: AsyncSession, organization_id: uuid.UUID
) -> Organization | None:
    """Retourne une organisation par son identifiant, ou None si elle est absente."""
    return await session.get(Organization, organization_id)


async def list_organization_ids(session: AsyncSession) -> list[uuid.UUID]:
    """Identifiants de toutes les organisations (alimente le worker de synchro)."""
    result = await session.execute(select(Organization.id))
    return list(result.scalars())


async def list_expired_demo_organizations(
    session: AsyncSession, *, now: datetime
) -> list[Organization]:
    """Organisations de démonstration arrivées à échéance (purge automatique)."""
    result = await session.execute(
        select(Organization).where(
            Organization.is_demo.is_(True),
            Organization.demo_expires_at <= now,
        )
    )
    return list(result.scalars())
