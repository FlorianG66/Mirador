"""Panneau web analytics de démonstration (sous-phase 5b, SPÉC §3 « Web analytics »).

Un petit écosystème cohérent et déterministe par seed : les sessions pilotent tout
le reste — visiteurs uniques (fraction), pages vues (sessions × pages/session),
conversions (taux), engagement et durée — et quatre répartitions (sources de
trafic, top pages, appareils, pays) somment exactement leur métrique parente.

Aucune vraie donnée ici (AGENTS.md §5) : les chemins de pages sont fictifs ; les
sources et appareils sont des clés canoniques traduites côté interface ; les pays
sont des codes ISO que l'interface nomme via `Intl.DisplayNames`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from typing import TypedDict

from app.connectors.mock import (
    CREATION_EPOCH,
    MockConnector,
    MockMetricConfig,
    daily_value,
    hash01,
)
from app.models.enums import Module
from app.schemas.metrics import PERIOD_DAY, MetricPoint, MetricSeries

# Les sessions portent la saisonnalité, le week-end et les anomalies ; toutes les
# autres métriques quotidiennes en dérivent jour par jour (cohérence exacte).
SESSIONS = MockMetricConfig(
    key="web.sessions",
    unit="sessions",
    base=4_200,
    trend=0.18,
    seasonality=0.10,
    weekend_factor=0.95,
    noise=0.12,
    decimals=0,
)

# Part des pages vues concentrée sur les pages les plus consultées (top N).
PAGES_SHARE = 0.60
TOP_PAGES_COUNT = 5

# Clés canoniques des répartitions (l'interface fournit le libellé selon la langue).
TRAFFIC_SOURCES: tuple[str, ...] = (
    "direct",
    "organic_search",
    "social",
    "referral",
    "email",
)
DEVICES: tuple[str, ...] = ("desktop", "mobile", "tablet")
COUNTRIES: tuple[str, ...] = ("FR", "BE", "CH", "LU", "CA")
# Chemins de pages fictifs : une petite entreprise a ses pages usuelles.
PAGES: tuple[str, ...] = (
    "/",
    "/tarifs",
    "/produit",
    "/blog",
    "/contact",
    "/a-propos",
    "/equipe",
    "/fonctionnalites",
)


class DistributionEntry(TypedDict):
    """Une entrée de répartition stockée dans les dimensions d'un point."""

    name: str
    value: float


def build_web_series(seed: int, since: datetime) -> list[MetricSeries]:
    """Les séries web analytics du jour de `since` (borné par l'époque) à aujourd'hui.

    Chaque jour produit un bloc cohérent : visiteurs ≤ sessions, pages vues ≥
    sessions, conversions ≤ sessions, et des répartitions qui somment exactement
    la métrique parente du jour.
    """
    start = since.date()
    if start < CREATION_EPOCH:
        start = CREATION_EPOCH
    today = datetime.now(UTC).date()
    if start > today:
        return []

    # Même top de pages sur toute la période (un widget garde les mêmes entrées).
    top_pages = ranked_names(seed, "web.top_pages", PAGES, TOP_PAGES_COUNT)

    sessions_pts: list[MetricPoint] = []
    visitors_pts: list[MetricPoint] = []
    pageviews_pts: list[MetricPoint] = []
    engagement_pts: list[MetricPoint] = []
    duration_pts: list[MetricPoint] = []
    conversions_pts: list[MetricPoint] = []
    sources_pts: list[MetricPoint] = []
    top_pages_pts: list[MetricPoint] = []
    devices_pts: list[MetricPoint] = []
    countries_pts: list[MetricPoint] = []

    for day in _days(start, today):
        at = datetime.combine(day, time.min, tzinfo=UTC)
        sessions = daily_value(seed, SESSIONS, day)

        # Dérivées du jour : bornes garanties par construction, indépendantes du seed.
        pages_per_session = 1.8 + 1.2 * hash01(seed, "web.pages_per_session", day)
        visitors = round(sessions * (0.78 + 0.12 * hash01(seed, "web.visitors", day)))
        pageviews = round(sessions * pages_per_session)
        conversions = round(sessions * (0.015 + 0.025 * hash01(seed, "web.conversions", day)))
        engagement_rate = round(45.0 + 20.0 * hash01(seed, "web.engagement_rate", day), 1)
        duration = round(90.0 + 150.0 * hash01(seed, "web.avg_session_duration", day))

        sessions_pts.append(MetricPoint(at=at, value=sessions))
        visitors_pts.append(MetricPoint(at=at, value=visitors))
        pageviews_pts.append(MetricPoint(at=at, value=pageviews))
        engagement_pts.append(MetricPoint(at=at, value=engagement_rate))
        duration_pts.append(MetricPoint(at=at, value=duration))
        conversions_pts.append(MetricPoint(at=at, value=conversions))
        sources_pts.append(
            _distribution_point(seed, "web.traffic_sources", TRAFFIC_SOURCES, sessions, at)
        )
        top_pages_pts.append(
            _distribution_point(seed, "web.top_pages", top_pages, pageviews * PAGES_SHARE, at)
        )
        devices_pts.append(_distribution_point(seed, "web.devices", DEVICES, visitors, at))
        countries_pts.append(_distribution_point(seed, "web.countries", COUNTRIES, visitors, at))

    return [
        MetricSeries(key="web.sessions", unit="sessions", period=PERIOD_DAY, points=sessions_pts),
        MetricSeries(key="web.visitors", unit="visitors", period=PERIOD_DAY, points=visitors_pts),
        MetricSeries(
            key="web.pageviews", unit="pageviews", period=PERIOD_DAY, points=pageviews_pts
        ),
        MetricSeries(key="web.engagement_rate", unit="%", period=PERIOD_DAY, points=engagement_pts),
        MetricSeries(
            key="web.avg_session_duration", unit="s", period=PERIOD_DAY, points=duration_pts
        ),
        MetricSeries(
            key="web.conversions", unit="conversions", period=PERIOD_DAY, points=conversions_pts
        ),
        MetricSeries(
            key="web.traffic_sources", unit="sessions", period=PERIOD_DAY, points=sources_pts
        ),
        MetricSeries(
            key="web.top_pages", unit="pageviews", period=PERIOD_DAY, points=top_pages_pts
        ),
        MetricSeries(key="web.devices", unit="visitors", period=PERIOD_DAY, points=devices_pts),
        MetricSeries(key="web.countries", unit="visitors", period=PERIOD_DAY, points=countries_pts),
    ]


def ranked_names(seed: int, key: str, pool: tuple[str, ...], count: int) -> tuple[str, ...]:
    """Les `count` entrées du pool au score déterministe le plus haut (classement stable)."""
    ranked = sorted(pool, key=lambda name: hash01(seed, key, "rank", name), reverse=True)
    return tuple(ranked[:count])


def _distribution_point(
    seed: int,
    key: str,
    labels: tuple[str, ...],
    total: float,
    at: datetime,
) -> MetricPoint:
    """Un point de répartition : le total exact dans `value`, le détail dans les
    dimensions (`items` : liste de `{name, value}`, triée par valeur décroissante)."""
    weights = [1.0 + 3.0 * hash01(seed, key, "weight", label) for label in labels]
    weight_sum = sum(weights)
    amounts = [round(total * weight / weight_sum, 2) for weight in weights]
    # L'arrondi au centime peut dériver : on ajuste la dernière entrée pour que la
    # somme du détail vaille exactement le total demandé.
    amounts[-1] = round(amounts[-1] + (round(total, 2) - sum(amounts)), 2)
    items: list[DistributionEntry] = [
        DistributionEntry(name=label, value=amount)
        for label, amount in zip(labels, amounts, strict=True)
    ]
    items.sort(key=lambda item: item["value"], reverse=True)
    return MetricPoint(
        at=at,
        value=round(sum(item["value"] for item in items), 2),
        dimensions={"items": items},
    )


class MockWebConnector(MockConnector):
    """Démo web analytics : panneau cohérent (SPÉC §3). Premier réel : Google Analytics 4."""

    provider = "mock.web"
    category = Module.WEB

    async def sync(self, since: datetime) -> list[MetricSeries]:
        """Les séries web analytics du jour de `since` au jour courant."""
        if self.seed is None:
            # Défense : un connecteur de démonstration n'a de sens que seedé.
            raise RuntimeError("Un connecteur de démonstration doit être instancié avec un seed.")
        return build_web_series(self.seed, since)


def _days(start: date, end: date) -> Iterator[date]:
    """Itère sur les jours inclus entre `start` et `end`."""
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)
