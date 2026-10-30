"""Repository : `chat_messages` (accès aux données uniquement, aucune règle métier).

Filtre explicite sur l'organisation **et** l'utilisateur : l'historique est
personnel (la RLS ne protège que la frontière entre organisations).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage


async def list_recent(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, limit: int
) -> list[ChatMessage]:
    """Les `limit` derniers messages de l'utilisateur, du plus ancien au plus récent."""
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.organization_id == organization_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def count_questions_since(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, since: datetime
) -> int:
    """Nombre de questions posées depuis `since` (base du quota journalier)."""
    result = await session.execute(
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.organization_id == organization_id,
            ChatMessage.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= since,
        )
    )
    return int(result.scalar_one())


async def add(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    content: str,
) -> ChatMessage:
    """Ajoute un message et le flushe (identifiant et date posés par la base)."""
    # Heure applicative : `now()` est figé par transaction, question et réponse
    # auraient la même date et un ordre d'historique aléatoire.
    message = ChatMessage(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        content=content,
        created_at=datetime.now(UTC),
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    return message
