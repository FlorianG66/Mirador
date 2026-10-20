"""Repository : `alert_rules` (règles d'alerte). Accès aux données uniquement."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_rule import AlertRule
from app.models.enums import AlertComparison


async def list_for_organization(
    session: AsyncSession, organization_id: uuid.UUID, *, enabled_only: bool = False
) -> list[AlertRule]:
    """Règles d'une organisation, de la plus ancienne à la plus récente (ordre stable)."""
    query = select(AlertRule).where(AlertRule.organization_id == organization_id)
    if enabled_only:
        query = query.where(AlertRule.enabled.is_(True))
    query = query.order_by(AlertRule.created_at, AlertRule.id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_by_id(
    session: AsyncSession, organization_id: uuid.UUID, rule_id: uuid.UUID
) -> AlertRule | None:
    """Règle si elle appartient bien à l'organisation (filtre explicite + RLS)."""
    result = await session.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id, AlertRule.organization_id == organization_id
        )
    )
    return result.scalar_one_or_none()


def create(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    metric_key: str,
    label: str | None,
    comparison: AlertComparison,
    threshold: float,
    period_days: int,
    enabled: bool,
) -> AlertRule:
    """Instancie une règle (non flushée) : le service la valide puis l'audite."""
    rule = AlertRule(
        organization_id=organization_id,
        metric_key=metric_key,
        label=label,
        comparison=comparison.value,
        threshold=threshold,
        period_days=period_days,
        enabled=enabled,
    )
    session.add(rule)
    return rule


async def delete(session: AsyncSession, rule: AlertRule) -> None:
    """Supprime une ligne ; le commit de la requête applique le changement."""
    await session.delete(rule)
