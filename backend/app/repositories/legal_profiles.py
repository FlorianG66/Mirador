"""Repository de la fiche légale (SPEC §5.3). Accès aux données uniquement."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_profile import LegalProfile


async def get_by_organization(
    session: AsyncSession, organization_id: uuid.UUID
) -> LegalProfile | None:
    """Fiche légale de l'organisation, ou `None` si elle n'a pas encore été créée."""
    statement = select(LegalProfile).where(LegalProfile.organization_id == organization_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


def create(session: AsyncSession, organization_id: uuid.UUID) -> LegalProfile:
    """Instancie une fiche vierge (non persistée) : le service la remplit puis la pose."""
    profile = LegalProfile(organization_id=organization_id)
    session.add(profile)
    return profile
