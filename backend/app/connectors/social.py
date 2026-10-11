"""Panneau réseaux sociaux de démonstration (sous-phase 5c, SPÉC §3 « Réseaux sociaux »).

Un petit écosystème cohérent et déterministe par seed : les abonnés par réseau
(cumul depuis l'époque de référence) donnent le total et sa croissance ; les
impressions, la portée, les interactions, le taux d'engagement, les meilleurs
posts et les mentions en dérivent jour par jour. Les publications suivent un
rythme hebdomadaire (moins de contenu le week-end).

Aucune vraie donnée ici (AGENTS.md §5) : les réseaux sont des clés canoniques
traduites côté interface ; les titres de posts sont fictifs et signalés comme
tels, comme les noms de clients du panneau financier.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from typing import TypedDict

from app.connectors.mock import (
    CREATION_EPOCH,
    MockConnector,
    MockMetricConfig,
    cumulative_value,
    hash01,
)
from app.models.enums import Module
from app.schemas.metrics import PERIOD_DAY, MetricPoint, MetricSeries

# Assise d'abonnés au 1er janvier 2020 (fictive) par réseau ; le cumul croît
# ensuite semaine après semaine (voir `cumulative_value`).
NETWORK_BASES: dict[str, int] = {
    "linkedin": 4_200,
    "instagram": 3_100,
    "facebook": 1_900,
    "x": 900,
    "youtube": 700,
}
NETWORKS: tuple[str, ...] = tuple(NETWORK_BASES)

_NETWORK_CONFIGS: dict[str, MockMetricConfig] = {
    network: MockMetricConfig(
        key=f"social.followers.{network}",
        unit="followers",
        base=base,
        trend=0.0,
        seasonality=0.0,
        weekend_factor=1.0,
        noise=0.0,
        cumulative=True,
    )
    for network, base in NETWORK_BASES.items()
}

# Part des interactions concentrée sur les meilleurs posts de la période.
TOP_POSTS_COUNT = 4
TOP_POSTS_SHARE = 0.45

# Titres de publications fictifs (aucune marque réelle) : le seed en choisit un
# sous-ensemble stable, comme le panneau finance choisit ses clients.
FICTIONAL_POSTS: tuple[str, ...] = (
    "Coulisses de notre atelier",
    "3 astuces pour gagner du temps",
    "Rencontre avec l'équipe support",
    "Nouveauté : notre offre d'automne",
    "Retour sur notre dernier salon",
    "Le guide du télétravail serein",
    "5 erreurs à éviter en gestion de projet",
    "Portrait : notre cheffe de projet",
    "Notre engagement écologique cette année",
    "Témoignage client : Maison Verte",
    "Dans les coulisses de la logistique",
    "Comment nous recrutons nos talents",
)


class DistributionEntry(TypedDict):
    """Une entrée de répartition stockée dans les dimensions d'un point."""

    name: str
    value: float


def build_social_series(seed: int, since: datetime) -> list[MetricSeries]:
    """Les séries sociales du jour de `since` (borné par l'époque) à aujourd'hui.

    Chaque jour produit un bloc cohérent : portée ≤ impressions, interactions
    ≤ impressions, taux d'engagement = interactions / impressions, et des
    répartitions (abonnés par réseau, meilleurs posts) qui somment exactement
    leur métrique parente.
    """
    start = since.date()
    if start < CREATION_EPOCH:
        start = CREATION_EPOCH
    today = datetime.now(UTC).date()
    if start > today:
        return []

    top_posts = ranked_names(seed, "social.top_posts", FICTIONAL_POSTS, TOP_POSTS_COUNT)

    followers_pts: list[MetricPoint] = []
    growth_pts: list[MetricPoint] = []
    impressions_pts: list[MetricPoint] = []
    reach_pts: list[MetricPoint] = []
    engagements_pts: list[MetricPoint] = []
    rate_pts: list[MetricPoint] = []
    mentions_pts: list[MetricPoint] = []
    posts_pts: list[MetricPoint] = []
    top_posts_pts: list[MetricPoint] = []

    # La veille du premier jour sert à calculer la croissance sans dépendre de
    # la fenêtre demandée (le cumul est absolu, comme pour la trésorerie).
    previous_total = _followers_total(seed, start - timedelta(days=1))
    for day in _days(start, today):
        at = datetime.combine(day, time.min, tzinfo=UTC)
        by_network = followers_by_network(seed, day)
        total = round(sum(by_network.values()), 2)
        growth = round(total - previous_total)
        previous_total = total

        # Le week-end, on publie moins : les impressions (donc la portée et les
        # interactions qui en découlent) baissent en conséquence.
        weekend_factor = 0.6 if day.weekday() >= 5 else 1.0
        impressions = round(
            total * (0.30 + 0.55 * hash01(seed, "social.impressions", day)) * weekend_factor
        )
        reach = round(impressions * (0.55 + 0.25 * hash01(seed, "social.reach", day)))
        engagements = round(
            impressions * (0.02 + 0.04 * hash01(seed, "social.engagement_rate", day))
        )
        engagement_rate = round(engagements / impressions * 100, 2) if impressions else 0.0
        mentions = round(total / 1000.0 * (1.5 + 2.5 * hash01(seed, "social.mentions", day)))

        followers_pts.append(_followers_point(by_network, at))
        growth_pts.append(MetricPoint(at=at, value=growth))
        impressions_pts.append(MetricPoint(at=at, value=impressions))
        reach_pts.append(MetricPoint(at=at, value=reach))
        engagements_pts.append(MetricPoint(at=at, value=engagements))
        rate_pts.append(MetricPoint(at=at, value=engagement_rate))
        mentions_pts.append(MetricPoint(at=at, value=mentions))
        posts_pts.append(MetricPoint(at=at, value=posts_for_day(seed, day)))
        top_posts_pts.append(
            _distribution_point(
                seed, "social.top_posts", top_posts, engagements * TOP_POSTS_SHARE, at
            )
        )

    return [
        MetricSeries(
            key="social.followers", unit="followers", period=PERIOD_DAY, points=followers_pts
        ),
        MetricSeries(
            key="social.followers_growth",
            unit="followers",
            period=PERIOD_DAY,
            points=growth_pts,
        ),
        MetricSeries(
            key="social.impressions", unit="impressions", period=PERIOD_DAY, points=impressions_pts
        ),
        MetricSeries(key="social.reach", unit="accounts", period=PERIOD_DAY, points=reach_pts),
        MetricSeries(
            key="social.engagements", unit="interactions", period=PERIOD_DAY, points=engagements_pts
        ),
        MetricSeries(key="social.engagement_rate", unit="%", period=PERIOD_DAY, points=rate_pts),
        MetricSeries(
            key="social.mentions", unit="mentions", period=PERIOD_DAY, points=mentions_pts
        ),
        MetricSeries(key="social.posts", unit="posts", period=PERIOD_DAY, points=posts_pts),
        MetricSeries(
            key="social.top_posts",
            unit="interactions",
            period=PERIOD_DAY,
            points=top_posts_pts,
        ),
    ]


class MockSocialConnector(MockConnector):
    """Démo réseaux sociaux : panneau cohérent (SPÉC §3). Premier réel : un réseau social."""

    provider = "mock.social"
    category = Module.SOCIAL

    async def sync(self, since: datetime) -> list[MetricSeries]:
        """Les séries sociales du jour de `since` au jour courant."""
        if self.seed is None:
            # Défense : un connecteur de démonstration n'a de sens que seedé.
            raise RuntimeError("Un connecteur de démonstration doit être instancié avec un seed.")
        return build_social_series(self.seed, since)


def followers_by_network(seed: int, day: date) -> dict[str, float]:
    """Abonnés cumulés par réseau à une date (valeur absolue, indépendante de la fenêtre)."""
    return {
        network: cumulative_value(seed, config, day) for network, config in _NETWORK_CONFIGS.items()
    }


def posts_for_day(seed: int, day: date) -> int:
    """Nombre de publications d'un jour (rythme hebdomadaire : week-end plus calme)."""
    roll = hash01(seed, "social.posts", day)
    if day.weekday() >= 5:
        return 1 if roll > 0.75 else 0
    return 2 if roll > 0.5 else 1


def ranked_names(seed: int, key: str, pool: tuple[str, ...], count: int) -> tuple[str, ...]:
    """Les `count` entrées du pool au score déterministe le plus haut (classement stable)."""
    ranked = sorted(pool, key=lambda name: hash01(seed, key, "rank", name), reverse=True)
    return tuple(ranked[:count])


def _followers_total(seed: int, day: date) -> float:
    """Total des abonnés à une date (somme des réseaux)."""
    return round(sum(followers_by_network(seed, day).values()), 2)


def _followers_point(by_network: dict[str, float], at: datetime) -> MetricPoint:
    """Un point « abonnés » : le total en valeur, le détail par réseau en dimensions."""
    items: list[DistributionEntry] = [
        DistributionEntry(name=network, value=value) for network, value in by_network.items()
    ]
    items.sort(key=lambda item: item["value"], reverse=True)
    return MetricPoint(
        at=at,
        value=round(sum(item["value"] for item in items), 2),
        dimensions={"items": items},
    )


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


def _days(start: date, end: date) -> Iterator[date]:
    """Itère sur les jours inclus entre `start` et `end`."""
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)
