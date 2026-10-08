"""Service du journal d'audit : trace et lecture des actions sensibles (AGENTS §5)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AUDIT_LOGS_LIMIT
from app.models.audit_log import AuditLog
from app.repositories import audit_logs as audit_logs_repository
from app.schemas.team import AuditLogOut


async def record(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Trace une action sensible ; l'organisation doit être posée (RLS)."""
    await audit_logs_repository.create(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
    )


async def list_recent(session: AsyncSession, *, organization_id: uuid.UUID) -> list[AuditLogOut]:
    """Journal de l'organisation, du plus récent au plus ancien."""
    entries: list[AuditLog] = await audit_logs_repository.list_recent(
        session, organization_id=organization_id, limit=AUDIT_LOGS_LIMIT
    )
    return [
        AuditLogOut(
            id=entry.id,
            action=entry.action,
            actor_user_id=entry.actor_user_id,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            payload=entry.payload,
            created_at=entry.created_at,
        )
        for entry in entries
    ]
