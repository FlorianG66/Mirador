"""Tests de la validation des métriques canoniques (SPEC §5.4)."""

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.models.enums import Module
from app.schemas.metrics import (
    PERIOD_DAY,
    MetricPoint,
    MetricSeries,
    build_metric_key,
    metric_prefix,
)


def _series(key: str, **overrides: Any) -> MetricSeries:
    """Série valide par défaut, dont on peut surcharger un champ."""
    base: dict[str, Any] = {"key": key, "unit": "EUR", "period": PERIOD_DAY}
    base.update(overrides)
    return MetricSeries.model_validate(base)


@pytest.mark.parametrize(
    "key",
    ["finance.revenue", "web.visits", "social.followers", "projects.tasks_done", "legal.docs"],
)
def test_cle_canonique_valide(key: str) -> None:
    assert _series(key).key == key


@pytest.mark.parametrize(
    "key",
    ["revenue", "finance.", "finance.revenu.e", "inconnu.x", "fi.nance.revenue", " finance.x"],
)
def test_cle_canonique_invalide(key: str) -> None:
    with pytest.raises(ValidationError):
        _series(key)


def test_point_accepte_dimensions() -> None:
    point = MetricPoint(
        at=datetime(2026, 1, 15, tzinfo=UTC),
        value=1200.5,
        dimensions={"channel": "organic", "device": "mobile"},
    )
    assert point.dimensions["channel"] == "organic"


def test_series_points_vides_par_defaut() -> None:
    assert _series("finance.revenue").points == []


def test_build_metric_key_et_prefixe() -> None:
    assert build_metric_key(Module.FINANCE, "revenue") == "finance.revenue"
    assert metric_prefix("finance.revenue") == "finance"
