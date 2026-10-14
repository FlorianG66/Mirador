"""Repository : `dashboard_layouts` (mise en page du tableau de bord). Accès aux données."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard_layout import DashboardLayout


async def get_for_user(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> DashboardLayout | None:
    """Disposition enregistrée d'un utilisateur, ou None s'il n'en a pas (défaut)."""
    result = await session.execute(
        select(DashboardLayout).where(
            DashboardLayout.organization_id == organization_id,
            DashboardLayout.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    widgets: list[dict[str, Any]],
) -> None:
    """Enregistre la disposition d'un utilisateur (créée ou remplacée, idempotent)."""
    statement = pg_insert(DashboardLayout).values(
        organization_id=organization_id,
        user_id=user_id,
        widgets=widgets,
    )
    statement = statement.on_conflict_do_update(
        constraint="dashboard_layouts_org_user",
        set_={"widgets": statement.excluded.widgets, "updated_at": func.now()},
    )
    await session.execute(statement)


async def delete_for_user(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Supprime la disposition d'un utilisateur ; True si une ligne existait."""
    # `RETURNING` : savoir si la suppression a bien eu un effet (ligne présente).
    result = await session.execute(
        delete(DashboardLayout)
        .where(
            DashboardLayout.organization_id == organization_id,
            DashboardLayout.user_id == user_id,
        )
        .returning(DashboardLayout.id)
    )
    return result.scalar_one_or_none() is not None
