"""Repository : `goals` (objectifs et budgets). Accès aux données uniquement."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import GoalDirection
from app.models.goal import Goal


async def list_for_organization(session: AsyncSession, organization_id: uuid.UUID) -> list[Goal]:
    """Objectifs d'une organisation, du plus ancien au plus récent (ordre stable)."""
    result = await session.execute(
        select(Goal)
        .where(Goal.organization_id == organization_id)
        .order_by(Goal.created_at, Goal.id)
    )
    return list(result.scalars().all())


async def get_by_id(
    session: AsyncSession, organization_id: uuid.UUID, goal_id: uuid.UUID
) -> Goal | None:
    """Objectif s'il appartient bien à l'organisation (filtre explicite + RLS)."""
    result = await session.execute(
        select(Goal).where(Goal.id == goal_id, Goal.organization_id == organization_id)
    )
    return result.scalar_one_or_none()


def create(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    metric_key: str,
    label: str | None,
    direction: GoalDirection,
    target_value: float,
    period_days: int,
) -> Goal:
    """Instancie un objectif (non flushé) : le service le valide puis l'audite."""
    goal = Goal(
        organization_id=organization_id,
        metric_key=metric_key,
        label=label,
        direction=direction.value,
        target_value=target_value,
        period_days=period_days,
    )
    session.add(goal)
    return goal


async def delete(session: AsyncSession, goal: Goal) -> None:
    """Supprime une ligne ; le commit de la requête applique le changement."""
    await session.delete(goal)
