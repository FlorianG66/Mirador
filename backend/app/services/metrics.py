"""Service de lecture des métriques (phase 4d) : série canonique depuis la base.

Uniquement la lecture : le tenant et la permission de module sont vérifiés par les
dépendances du routeur (défense en profondeur, la RLS s'en charge aussi).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import metric_snapshots as metric_snapshots_repository
from app.schemas.metrics import (
    MetricAggregation,
    MetricComparison,
    MetricComparisonSummary,
    MetricPoint,
    MetricSeries,
)
from app.services.errors import ServiceProblem
from app.services.metric_catalog import aggregation_for


async def get_metric_series(
    session: AsyncSession,
    organization_id: uuid.UUID,
    metric_key: str,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
) -> MetricSeries:
    """Retourne la série d'une métrique, triée chronologiquement (fenêtre + limite).

    Clé inconnue ou sans donnée → 404 : le format de la clé est déjà validé en
    amont (dépendance du routeur), et une organisation synchronisée a forcément
    des points pour les modules présents dans le registre.
    """
    if start is not None and end is not None and end < start:
        raise ServiceProblem(422, "« end » précède « start ».")
    snapshots = await metric_snapshots_repository.get_series(
        session,
        organization_id,
        metric_key,
        start=start,
        end=end,
        limit=limit,
    )
    if not snapshots:
        raise ServiceProblem(404, "Aucune donnée pour cette métrique.")
    points = [
        MetricPoint(at=snapshot.captured_at, value=snapshot.value, dimensions=snapshot.dimensions)
        for snapshot in snapshots
    ]
    return MetricSeries(
        key=metric_key,
        unit=snapshots[0].unit,
        period=snapshots[0].period,
        points=points,
    )


def _aggregate(values: list[float], aggregation: MetricAggregation) -> float:
    """Réduit une fenêtre de valeurs (ordonnées chronologiquement) à une valeur."""
    if not values:
        return 0.0
    if aggregation == MetricAggregation.LAST:
        return values[-1]
    if aggregation == MetricAggregation.AVERAGE:
        return sum(values) / len(values)
    return sum(values)


async def get_metric_comparison(
    session: AsyncSession,
    organization_id: uuid.UUID,
    metric_key: str,
    *,
    days: int,
    end: datetime | None = None,
) -> MetricComparison:
    """Compare une métrique sur `days` jours aux `days` jours qui précèdent.

    Une seule lecture couvre les deux fenêtres, séparées à la frontière
    `end - days`. La valeur de chaque fenêtre est réduite selon le catalogue
    (`sum` pour un flux, `last` pour un niveau, `average` pour un taux). Une
    métrique sans aucun point sur la double fenêtre → 404, comme la lecture.
    """
    window_end = end if end is not None else datetime.now(UTC)
    current_start = window_end - timedelta(days=days)
    window_start = current_start - timedelta(days=days)
    snapshots = await metric_snapshots_repository.get_series(
        session,
        organization_id,
        metric_key,
        start=window_start,
        end=window_end,
        limit=days * 2 + 10,
    )
    if not snapshots:
        raise ServiceProblem(404, "Aucune donnée pour cette métrique.")

    current_snapshots = [row for row in snapshots if row.captured_at > current_start]
    previous_snapshots = [row for row in snapshots if row.captured_at <= current_start]
    aggregation = aggregation_for(metric_key)
    current_value = _aggregate([row.value for row in current_snapshots], aggregation)
    previous_value = _aggregate([row.value for row in previous_snapshots], aggregation)

    change = round(current_value - previous_value, 2)
    change_percent = (
        round((current_value - previous_value) / abs(previous_value) * 100, 2)
        if previous_value != 0
        else None
    )
    latest = snapshots[-1]
    return MetricComparison(
        key=metric_key,
        unit=latest.unit,
        period=latest.period,
        aggregation=aggregation,
        days=days,
        current=[
            MetricPoint(at=row.captured_at, value=row.value, dimensions=row.dimensions)
            for row in current_snapshots
        ],
        previous=[
            MetricPoint(at=row.captured_at, value=row.value, dimensions=row.dimensions)
            for row in previous_snapshots
        ],
        summary=MetricComparisonSummary(
            current_value=round(current_value, 2),
            previous_value=round(previous_value, 2),
            change=change,
            change_percent=change_percent,
        ),
    )
