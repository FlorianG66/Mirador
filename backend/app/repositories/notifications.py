"""Repository : notifications (accès aux données uniquement, aucune règle métier).

Le destinataire est forcément `user_id`. Toutes les requêtes sont filtrées par
organisation (RLS à titre de défense en profondeur + filtres explicites).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def get_unread_count(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> int:
    """Nombre de notifications non lues pour un utilisateur dans son organisation."""
    result = await session.execute(
        select(func.count(Notification.id)).where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
    )
    return int(result.scalar_one())


async def list_notifications(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    """Liste chronologique des notifications d'un utilisateur (les plus récentes en premier)."""
    result = await session.execute(
        select(Notification)
        .where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
        )
        .order_by(Notification.created_at.desc(), Notification.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_for_user(
    session: AsyncSession,
    *,
    notification_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    """Récupère une notification appartenant explicitement à ce destinataire."""
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def mark_read(session: AsyncSession, notification: Notification) -> None:
    """Marque une notification comme lue (idempotent si déjà lue)."""
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await session.flush()


async def mark_all_read(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Marque toutes les notifications d'un utilisateur comme lues."""
    await session.execute(
        update(Notification)
        .where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    await session.flush()


async def get_existing_dedup(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    dedup_key: str,
) -> Notification | None:
    """Vérifie s'il existe déjà une notification non lue avec cette clé de déduplication."""
    result = await session.execute(
        select(Notification).where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
            Notification.dedup_key == dedup_key,
            Notification.read_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def create_notification(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    kind: str,
    params: dict[str, object],
    link: str | None = None,
    dedup_key: str | None = None,
) -> Notification:
    """Crée une notification (flush immédiat, commit par la session appelante)."""
    notification = Notification(
        organization_id=organization_id,
        user_id=user_id,
        kind=kind,
        params=params,
        link=link,
        dedup_key=dedup_key,
    )
    session.add(notification)
    await session.flush()
    return notification
