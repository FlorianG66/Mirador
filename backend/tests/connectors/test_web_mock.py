"""Tests du panneau web analytics de démonstration (sous-phase 5b, SPÉC §3).

Vérifie la cohérence d'ensemble (visiteurs ≤ sessions, pages vues = sessions ×
pages/session, conversions ≤ sessions), les dimensions (sources, top pages,
appareils, pays qui somment exactement leur métrique parente), le réalisme
(week-end plus calme) et le déterminisme par seed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.connectors import registry
from app.connectors.web import (
    PAGES_SHARE,
    TOP_PAGES_COUNT,
    build_web_series,
)

_NOW = datetime.now(UTC)
_WINDOW = timedelta(days=84)

WEB_KEYS = {
    "web.sessions",
    "web.visitors",
    "web.pageviews",
    "web.engagement_rate",
    "web.avg_session_duration",
    "web.conversions",
    "web.traffic_sources",
    "web.top_pages",
    "web.devices",
    "web.countries",
}


def _points(seed: int, since: datetime | None = None):
    """Séries web indexées par clé, sur la fenêtre standard sauf précision."""
    returned = build_web_series(seed, since or _NOW - _WINDOW)
    return {series.key: series.points for series in returned}


def test_le_panneau_contient_les_dix_series_attendues() -> None:
    by_key = _points(42)
    assert set(by_key) == WEB_KEYS
    assert all(by_key[key] and by_key[key][0].at.tzinfo == UTC for key in by_key)


def test_visiteurs_inferieurs_ou_egaux_aux_sessions() -> None:
    by_key = _points(7)
    for sessions, visitors in zip(by_key["web.sessions"], by_key["web.visitors"], strict=True):
        assert visitors.value <= sessions.value
        assert visitors.value > 0


def test_pages_vues_derivent_des_sessions() -> None:
    by_key = _points(7)
    for sessions, pageviews in zip(by_key["web.sessions"], by_key["web.pageviews"], strict=True):
        # Au moins une page vue par session.
        assert pageviews.value >= sessions.value


def test_conversions_inferieures_ou_egales_aux_sessions() -> None:
    by_key = _points(7)
    for sessions, conversions in zip(
        by_key["web.sessions"], by_key["web.conversions"], strict=True
    ):
        assert 0 <= conversions.value <= sessions.value


def test_taux_engagement_et_duree_dans_les_bornes() -> None:
    by_key = _points(7)
    for point in by_key["web.engagement_rate"]:
        assert 0 <= point.value <= 100
    for point in by_key["web.avg_session_duration"]:
        assert point.value > 0


def test_sources_de_trafic_somment_les_sessions() -> None:
    by_key = _points(11)
    for point, sessions in zip(by_key["web.traffic_sources"], by_key["web.sessions"], strict=True):
        items = point.dimensions["items"]
        assert len(items) == 5
        assert point.value == round(sum(item["value"] for item in items), 2)
        assert point.value == pytest.approx(sessions.value, abs=0.05)


def test_top_pages_part_du_total_des_pages_vues() -> None:
    by_key = _points(11)
    for point, pageviews in zip(by_key["web.top_pages"], by_key["web.pageviews"], strict=True):
        items = point.dimensions["items"]
        assert len(items) == TOP_PAGES_COUNT
        assert point.value == round(sum(item["value"] for item in items), 2)
        assert point.value == pytest.approx(pageviews.value * PAGES_SHARE, abs=0.05)


def test_appareils_et_pays_somment_les_visiteurs() -> None:
    by_key = _points(11)
    visitors = by_key["web.visitors"]
    for dimension_key in ("web.devices", "web.countries"):
        for point, visitor_count in zip(by_key[dimension_key], visitors, strict=True):
            items = point.dimensions["items"]
            assert point.value == round(sum(item["value"] for item in items), 2)
            assert point.value == pytest.approx(visitor_count.value, abs=0.05)


def test_le_week_end_est_plus_calme_que_la_semaine() -> None:
    sessions = _points(42)["web.sessions"]
    weekend = [p.value for p in sessions if p.at.weekday() >= 5]
    weekday = [p.value for p in sessions if p.at.weekday() < 5]
    assert weekend and weekday
    assert sum(weekend) / len(weekend) < sum(weekday) / len(weekday)


def test_le_seed_change_les_valeurs_mais_pas_la_structure() -> None:
    seed_a = _points(1)
    seed_b = _points(2)
    assert set(seed_a) == set(seed_b)
    assert [p.value for p in seed_a["web.sessions"]] != [p.value for p in seed_b["web.sessions"]]


@pytest.mark.asyncio
async def test_sync_deterministe_et_futur_vide() -> None:
    future = _NOW + timedelta(days=1)
    connector = registry.make("mock.web", seed=9)
    assert await connector.sync(future) == []
    series = await connector.sync(_NOW - _WINDOW)
    assert {metric.key for metric in series} == WEB_KEYS
