"""Repositories des snapshots de métriques (SPEC §5.3). Accès aux données uniquement."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric_snapshot import MetricSnapshot
from app.schemas.metrics import MetricSnapshotIn

# Un INSERT … VALUES est limité à 32 767 arguments par asyncpg. Chaque ligne en
# pose 7 (hors valeurs par défaut) : on découpe par lots largement sous la limite,
# sinon la synchronisation d'un panneau riche (web + finance) échoue d'un bloc.
_MAX_ROWS_PER_STATEMENT = 2_000


async def upsert_many(
    session: AsyncSession, organization_id: uuid.UUID, snapshots: list[MetricSnapshotIn]
) -> int:
    """Écrit les points par lots, sans doublon (idempotent).

    La contrainte (organization_id, metric_key, captured_at) sert de cible de
    conflit : une re-synchronisation remplace la valeur au lieu d'ajouter une
    ligne. Le filtre explicite par organisation s'ajoute à la RLS (double filtre).
    """
    if not snapshots:
        return 0
    rows = [
        {
            "organization_id": organization_id,
            "metric_key": snapshot.metric_key,
            "unit": snapshot.unit,
            "period": snapshot.period,
            "value": snapshot.value,
            "dimensions": snapshot.dimensions,
            "captured_at": snapshot.captured_at,
        }
        for snapshot in snapshots
    ]
    for start in range(0, len(rows), _MAX_ROWS_PER_STATEMENT):
        chunk = rows[start : start + _MAX_ROWS_PER_STATEMENT]
        statement = pg_insert(MetricSnapshot).values(chunk)
        statement = statement.on_conflict_do_update(
            constraint="metric_snapshots_org_key_at",
            set_={
                "unit": statement.excluded.unit,
                "value": statement.excluded.value,
                "dimensions": statement.excluded.dimensions,
            },
        )
        await session.execute(statement)
    return len(rows)


async def get_series(
    session: AsyncSession,
    organization_id: uuid.UUID,
    metric_key: str,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 1000,
) -> list[MetricSnapshot]:
    """Points d'une métrique, triés par date croissante (fenêtre et limite optionnelles)."""
    statement = select(MetricSnapshot).where(
        MetricSnapshot.organization_id == organization_id,
        MetricSnapshot.metric_key == metric_key,
    )
    if start is not None:
        statement = statement.where(MetricSnapshot.captured_at >= start)
    if end is not None:
        statement = statement.where(MetricSnapshot.captured_at <= end)
    statement = statement.order_by(MetricSnapshot.captured_at).limit(limit)
    result = await session.execute(statement)
    return list(result.scalars())


async def get_latest(
    session: AsyncSession,
    organization_id: uuid.UUID,
    metric_key: str,
    *,
    limit: int = 1,
) -> list[MetricSnapshot]:
    """Points les plus récents d'une métrique, du plus récent au plus ancien.

    `get_series` trie en ordre croissant : pour un KPI du Pouls on veut l'inverse
    (le dernier point d'abord), d'où cette lecture dédiée.
    """
    statement = (
        select(MetricSnapshot)
        .where(
            MetricSnapshot.organization_id == organization_id,
            MetricSnapshot.metric_key == metric_key,
        )
        .order_by(MetricSnapshot.captured_at.desc())
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.scalars())
