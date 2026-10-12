"""Tests du panneau réseaux sociaux de démonstration (sous-phase 5c, SPÉC §3).

Vérifie la cohérence d'ensemble (portée ≤ impressions, interactions ≤
impressions, taux d'engagement = interactions / impressions, croissance =
variation des abonnés), les dimensions (abonnés par réseau et meilleurs posts
qui somment exactement leur métrique parente), le réalisme (week-end plus
calme) et le déterminisme par seed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.connectors import registry
from app.connectors.social import (
    NETWORKS,
    TOP_POSTS_COUNT,
    TOP_POSTS_SHARE,
    build_social_series,
)

_NOW = datetime.now(UTC)
_WINDOW = timedelta(days=84)

SOCIAL_KEYS = {
    "social.followers",
    "social.followers_growth",
    "social.impressions",
    "social.reach",
    "social.engagements",
    "social.engagement_rate",
    "social.mentions",
    "social.posts",
    "social.top_posts",
}


def _points(seed: int, since: datetime | None = None):
    """Séries sociales indexées par clé, sur la fenêtre standard sauf précision."""
    returned = build_social_series(seed, since or _NOW - _WINDOW)
    return {series.key: series.points for series in returned}


def test_le_panneau_contient_les_niveaux_series_attendues() -> None:
    by_key = _points(42)
    assert set(by_key) == SOCIAL_KEYS
    assert all(by_key[key] and by_key[key][0].at.tzinfo == UTC for key in by_key)


def test_abonnes_par_reseau_somment_le_total() -> None:
    by_key = _points(11)
    for point in by_key["social.followers"]:
        items = point.dimensions["items"]
        assert len(items) == len(NETWORKS)
        assert {item["name"] for item in items} == set(NETWORKS)
        assert point.value == round(sum(item["value"] for item in items), 2)


def test_abonnes_cumules_croissants() -> None:
    followers = [point.value for point in _points(42)["social.followers"]]
    assert followers == sorted(followers)  # cumul : jamais de baisse
    assert followers[-1] > followers[0]


def test_croissance_est_la_variation_des_abonnes() -> None:
    by_key = _points(7)
    followers = by_key["social.followers"]
    growth = by_key["social.followers_growth"]
    for index, point in enumerate(growth):
        assert point.value >= 0
        if index > 0:
            assert point.value == pytest.approx(
                followers[index].value - followers[index - 1].value, abs=0.01
            )


def test_portee_inferieure_ou_egale_aux_impressions() -> None:
    by_key = _points(7)
    pairs = zip(by_key["social.impressions"], by_key["social.reach"], strict=True)
    for impressions, reach in pairs:
        assert 0 < reach.value <= impressions.value


def test_interactions_inferieures_ou_egales_aux_impressions() -> None:
    by_key = _points(7)
    for impressions, engagements in zip(
        by_key["social.impressions"], by_key["social.engagements"], strict=True
    ):
        assert 0 <= engagements.value <= impressions.value


def test_taux_engagement_derive_des_interactions() -> None:
    by_key = _points(7)
    for impressions, engagements, rate in zip(
        by_key["social.impressions"],
        by_key["social.engagements"],
        by_key["social.engagement_rate"],
        strict=True,
    ):
        assert 0 <= rate.value <= 100
        expected = round(engagements.value / impressions.value * 100, 2)
        assert rate.value == pytest.approx(expected, abs=0.01)


def test_meilleurs_posts_partagent_les_interactions() -> None:
    by_key = _points(11)
    for point, engagements in zip(
        by_key["social.top_posts"], by_key["social.engagements"], strict=True
    ):
        items = point.dimensions["items"]
        assert len(items) == TOP_POSTS_COUNT
        assert point.value == round(sum(item["value"] for item in items), 2)
        assert point.value == pytest.approx(engagements.value * TOP_POSTS_SHARE, abs=0.05)


def test_mentions_positives() -> None:
    mentions = _points(7)["social.mentions"]
    assert mentions
    assert all(point.value >= 0 for point in mentions)
    assert any(point.value > 0 for point in mentions)


def test_le_week_end_est_plus_calme_que_la_semaine() -> None:
    by_key = _points(42)
    for key in ("social.impressions", "social.posts"):
        points = by_key[key]
        weekend = [p.value for p in points if p.at.weekday() >= 5]
        weekday = [p.value for p in points if p.at.weekday() < 5]
        assert weekend and weekday
        assert sum(weekend) / len(weekend) < sum(weekday) / len(weekday)


def test_le_seed_change_les_valeurs_mais_pas_la_structure() -> None:
    seed_a = _points(1)
    seed_b = _points(2)
    assert set(seed_a) == set(seed_b)
    assert [p.value for p in seed_a["social.impressions"]] != [
        p.value for p in seed_b["social.impressions"]
    ]


@pytest.mark.asyncio
async def test_sync_deterministe_et_futur_vide() -> None:
    future = _NOW + timedelta(days=1)
    connector = registry.make("mock.social", seed=9)
    assert await connector.sync(future) == []
    series = await connector.sync(_NOW - _WINDOW)
    assert {metric.key for metric in series} == SOCIAL_KEYS
