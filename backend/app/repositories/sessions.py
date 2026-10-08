"""Repository : sessions (accès aux données uniquement, aucune règle métier)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import UserSession


async def create_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    access_token_hash: str,
    refresh_token_hash: str,
    csrf_token: str,
    access_expires_at: datetime,
    refresh_expires_at: datetime,
) -> UserSession:
    """Insère une session. Flush seulement : le commit appartient à la requête."""
    row = UserSession(
        user_id=user_id,
        access_token_hash=access_token_hash,
        refresh_token_hash=refresh_token_hash,
        csrf_token=csrf_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )
    session.add(row)
    await session.flush()
    return row


async def get_by_access_hash(session: AsyncSession, access_token_hash: str) -> UserSession | None:
    """Retrouve la session portant cet hachage d'accès, ou None."""
    result = await session.execute(
        select(UserSession).where(UserSession.access_token_hash == access_token_hash)
    )
    return result.scalar_one_or_none()


async def get_by_refresh_hash(session: AsyncSession, refresh_token_hash: str) -> UserSession | None:
    """Retrouve la session portant cet hachage de rafraîchissement, ou None."""
    result = await session.execute(
        select(UserSession).where(UserSession.refresh_token_hash == refresh_token_hash)
    )
    return result.scalar_one_or_none()


async def rotate(
    session: AsyncSession,
    row: UserSession,
    *,
    access_token_hash: str,
    refresh_token_hash: str,
    access_expires_at: datetime,
    refresh_expires_at: datetime,
) -> None:
    """Remplace les deux jetons : l'ancien rafraîchissement devient inutilisable."""
    await session.execute(
        update(UserSession)
        .where(UserSession.id == row.id)
        .values(
            access_token_hash=access_token_hash,
            refresh_token_hash=refresh_token_hash,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
        )
    )
    await session.refresh(row)


async def revoke(session: AsyncSession, row: UserSession) -> None:
    """Marque la session comme révoquée (déconnexion, fuite suspecte)."""
    await session.execute(
        update(UserSession).where(UserSession.id == row.id).values(revoked_at=func.now())
    )
