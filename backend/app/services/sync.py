"""Service de synchronisation des connecteurs : objectif, exécution, idempotence.

Il fait le lien entre le registre (SPEC §5.4), qui sait *produire* des métriques
canoniques, et les `metric_snapshots` (SPEC §5.3), qui les *stockent*. Le worker
(phase 4c) n'a qu'à appeler `sync_organization` pour une organisation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import registry
from app.repositories import metric_snapshots as metric_snapshots_repository
from app.schemas.metrics import MetricSnapshotIn

# Nombre de jours de données fictives (re)écrits à chaque synchronisation. La
# réécriture est idempotente (upsert) : aucune borne haute « dernière synchro »
# à tenir au MVP, et une organisation peut toujours reculer dans son historique.
SYNC_LOOKBACK_DAYS = 365


def seed_for_organization(organization_id: uuid.UUID) -> int:
    """Seed déterministe d'une organisation : les mêmes données à chaque appel.

    Dérivé des 32 bits faibles de l'identifiant : stable, et cela suffit à
    différencier largement les organisations de démonstration entre elles.
    """
    return organization_id.int & 0xFFFFFFFF


async def sync_organization(session: AsyncSession, organization_id: uuid.UUID) -> int:
    """Synchronise toutes les démos enregistrées et range les points en base.

    Retourne le nombre de points appliqués (upserts). Le tenant doit être posé
    sur la session (c'est la RLS qui autorise l'écriture)."""
    since = datetime.now(UTC) - timedelta(days=SYNC_LOOKBACK_DAYS)
    connectors = registry.make_all(seed=seed_for_organization(organization_id))

    snapshots: list[MetricSnapshotIn] = []
    for instance in connectors:
        for series in await instance.sync(since):
            for point in series.points:
                snapshots.append(
                    MetricSnapshotIn(
                        metric_key=series.key,
                        period=series.period,
                        value=point.value,
                        dimensions=point.dimensions,
                        captured_at=point.at,
                    )
                )
    return await metric_snapshots_repository.upsert_many(session, organization_id, snapshots)
