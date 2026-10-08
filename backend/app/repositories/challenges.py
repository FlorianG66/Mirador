"""Repository : défis d'authentification A2F (accès aux données uniquement)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_challenge import AuthChallenge


async def create_auth_challenge(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> AuthChallenge:
    """Enregistre le défi. Flush seulement : le commit appartient à la requête."""
    row = AuthChallenge(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(row)
    await session.flush()
    return row


async def get_by_token_hash(session: AsyncSession, token_hash: str) -> AuthChallenge | None:
    """Retrouve le défi portant ce hachage, ou None."""
    result = await session.execute(
        select(AuthChallenge).where(AuthChallenge.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def mark_used(session: AsyncSession, row: AuthChallenge) -> None:
    """Consomme le défi : il ne peut pas être rejoué après la connexion."""
    await session.execute(
        update(AuthChallenge).where(AuthChallenge.id == row.id).values(used_at=func.now())
    )
