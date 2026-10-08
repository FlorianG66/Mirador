"""Repository : jetons de réinitialisation de mot de passe (phase 2c)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


async def create_token(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetToken:
    """Enregistre le jeton. Flush seulement : le commit appartient à la requête."""
    row = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(row)
    await session.flush()
    return row


async def get_by_token_hash(session: AsyncSession, token_hash: str) -> PasswordResetToken | None:
    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def mark_used(session: AsyncSession, row: PasswordResetToken) -> None:
    """Consomme le jeton : une réinitialisation ne se fait qu'une fois."""
    await session.execute(
        update(PasswordResetToken).where(PasswordResetToken.id == row.id).values(used_at=func.now())
    )
