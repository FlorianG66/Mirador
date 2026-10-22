"""Repository : liens de démonstration (accès aux données uniquement)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.demo_link import DemoLink


async def create_demo_link(
    session: AsyncSession,
    *,
    sector: str,
    token_hash: str,
    expires_at: datetime,
    organization_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
) -> DemoLink:
    """Insère un lien. Flush seulement : le commit appartient à la requête."""
    link = DemoLink(
        sector=sector,
        token_hash=token_hash,
        expires_at=expires_at,
        organization_id=organization_id,
        created_by_user_id=created_by_user_id,
    )
    session.add(link)
    await session.flush()
    return link


async def get_by_token_hash(session: AsyncSession, token_hash: str) -> DemoLink | None:
    """Lien correspondant au jeton présenté (jamais le jeton en clair)."""
    result = await session.execute(select(DemoLink).where(DemoLink.token_hash == token_hash))
    return result.scalar_one_or_none()


async def delete_expired(session: AsyncSession, *, now: datetime) -> int:
    """Supprime les liens échus ; retourne le nombre de lignes effacées."""
    result = await session.execute(delete(DemoLink).where(DemoLink.expires_at <= now))
    # Un DELETE sans RETURNING renvoie un CursorResult : `rowcount` y est défini.
    return int(getattr(result, "rowcount", 0) or 0)
