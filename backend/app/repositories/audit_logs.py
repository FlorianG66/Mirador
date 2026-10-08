"""Repository : audit_logs (journal des actions sensibles, AGENTS.md §5)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def create(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    """Ajoute une entrée au journal. Flush seulement (RLS : tenant posé)."""
    entry = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
    )
    session.add(entry)
    await session.flush()
    return entry


async def list_recent(
    session: AsyncSession, *, organization_id: uuid.UUID, limit: int
) -> list[AuditLog]:
    """Entrées les plus récentes d'une organisation, dans l'ordre anté-chronologique."""
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == organization_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id)
        .limit(limit)
    )
    return list(result.scalars().all())
