"""Repository : organisations (accès aux données uniquement, aucune règle métier)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


async def create_organization(
    session: AsyncSession, *, name: str, siren: str | None = None
) -> Organization:
    """Insère une organisation. Flush seulement : le commit appartient à la requête."""
    organization = Organization(name=name, siren=siren)
    session.add(organization)
    await session.flush()
    return organization


async def get_organization(
    session: AsyncSession, organization_id: uuid.UUID
) -> Organization | None:
    """Retourne une organisation par son identifiant, ou None si elle est absente."""
    return await session.get(Organization, organization_id)
