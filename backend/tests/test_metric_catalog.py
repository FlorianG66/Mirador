"""Tests du catalogue d'agrégation des métriques (phase 6a).

Le catalogue décide comment réduire une fenêtre (flux → somme, niveau → dernière
valeur, taux → moyenne). Le test le plus important vérifie qu'aucune métrique des
connecteurs n'est oubliée : une clé absente retomberait silencieusement sur la
somme et fausserait la comparaison de périodes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.connectors import (
    build_finance_series,
    build_projects_series,
    build_social_series,
    build_web_series,
)
from app.schemas.metrics import MetricAggregation
from app.services.metric_catalog import METRIC_AGGREGATIONS, aggregation_for


def test_le_catalogue_couvre_toutes_les_metriques_des_connecteurs() -> None:
    """Toute clé produite par un connecteur est classée (aucune omission muette)."""
    since = datetime.now(UTC) - timedelta(days=2)
    series = [
        *build_finance_series(1, since),
        *build_web_series(1, since),
        *build_social_series(1, since),
        *build_projects_series(1, since),
    ]
    keys = {item.key for item in series}
    # Garde-fou : les connecteurs doivent produire des séries pour que le test ait du sens.
    assert keys
    assert keys <= set(METRIC_AGGREGATIONS), sorted(keys - set(METRIC_AGGREGATIONS))


@pytest.mark.parametrize(
    ("metric_key", "expected"),
    [
        ("finance.revenue", MetricAggregation.SUM),
        ("finance.cash", MetricAggregation.LAST),
        ("social.followers", MetricAggregation.LAST),
        ("projects.open_tasks", MetricAggregation.LAST),
        ("web.engagement_rate", MetricAggregation.AVERAGE),
        ("projects.avg_progress", MetricAggregation.AVERAGE),
        # Clé inconnue : repli sur la somme, le cas courant.
        ("inconnu.metric", MetricAggregation.SUM),
    ],
)
def test_agregation_attendue(metric_key: str, expected: MetricAggregation) -> None:
    assert aggregation_for(metric_key) == expected
