"""Service de lecture des métriques (phase 4d) : série canonique depuis la base.

Uniquement la lecture : le tenant et la permission de module sont vérifiés par les
dépendances du routeur (défense en profondeur, la RLS s'en charge aussi).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import metric_snapshots as metric_snapshots_repository
from app.schemas.metrics import MetricPoint, MetricSeries
from app.services.errors import ServiceProblem


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
