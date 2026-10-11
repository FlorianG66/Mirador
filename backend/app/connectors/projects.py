"""Panneau projets & tâches de démonstration (sous-phase 5d, SPÉC §3 « Projets & tâches »).

Un petit écosystème cohérent et déterministe par seed : avec plus de tâches
créées que de terminées chaque trimestre, le stock de tâches ouvertes croît ;
les retards, les répartitions par statut et par personne en dérivent (la charge
par personne s'étale uniformément), tandis que l'avancement moyen, le délai
moyen de livraison, les projets actifs et les jalons à venir complètent le
tableau. Le week-end, l'équipe termine moins de tâches.

Aucune vraie donnée ici (AGENTS.md §5) : les statuts sont des clés canoniques
traduites côté interface, les noms de personnes fictifs et les jalons génériques.
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

# Statuts canoniques des tâches : chaînés côté interface via `projects.status.*`.
STATUSES: tuple[str, ...] = ("todo", "in_progress", "review", "blocked")

# Équipe fictive (aucun salarié réel, AGENTS.md §5) : la charge se répartit
# entre ces personnes. Le seed garde le même classement d'un jour à l'autre.
PERSONS: tuple[str, ...] = (
    "Camille Moreau",
    "Lucas Bernard",
    "Inès Robert",
    "Naomi Petit",
    "Hugo Dubois",
    "Lina Girard",
)

# Jalons à venir génériques (projets fictifs, aucune marque ni client réel).
MILESTONES: tuple[str, ...] = (
    "Recette finale",
    "Déploiement bêta",
    "Livraison du module M1",
    "Ouverture du nouveau client",
    "Audit technique",
    "Formation des équipes",
)

# Tâches ouvertes « en stock » au 1er janvier 2020 (fictif) : le cumul des
# créées moins les terminées reste ainsi nettement positif.
INITIAL_BACKLOG = 40

_CREATED_CONFIG = MockMetricConfig(
    key="projects.tasks_created",
    unit="tasks",
    base=18,
    trend=0.08,
    seasonality=0.08,
    weekend_factor=0.15,
    noise=0.30,
)
_DONE_CONFIG = MockMetricConfig(
    key="projects.tasks_done",
    unit="tasks",
    base=16,
    trend=0.08,
    seasonality=0.08,
    weekend_factor=0.20,
    noise=0.30,
)
_COMPLETION_CONFIG = MockMetricConfig(
    key="projects.avg_completion_time",
    unit="days",
    base=6.5,
    trend=0.0,
    seasonality=0.0,
    weekend_factor=1.0,
    noise=0.15,
    decimals=1,
    anomalies=False,
)
_PROGRESS_CONFIG = MockMetricConfig(
    key="projects.avg_progress",
    unit="%",
    base=55,
    trend=0.0,
    seasonality=0.0,
    weekend_factor=1.0,
    noise=0.10,
    decimals=0,
    anomalies=False,
)
_ACTIVE_CONFIG = MockMetricConfig(
    key="projects.active_projects",
    unit="projects",
    base=9,
    trend=0.05,
    seasonality=0.0,
    weekend_factor=1.0,
    noise=0.15,
)


class DistributionEntry(TypedDict):
    """Une entrée de répartition stockée dans les dimensions d'un point."""

    name: str
    value: float


def build_projects_series(seed: int, since: datetime) -> list[MetricSeries]:
    """Les séries projets & tâches du jour de `since` (borné par l'époque) à aujourd'hui.

    Chaque jour produit un bloc cohérent : le stock ouvert est la différence
    cumulée des créées moins les terminées (jamais négatif), les retards
    n'excèdent jamais le stock, et les répartitions (statut, personne, jalons)
    somment exactement leur métrique parente.
    """
    start = since.date()
    if start < CREATION_EPOCH:
        start = CREATION_EPOCH
    today = datetime.now(UTC).date()
    if start > today:
        return []

    created_pts: list[MetricPoint] = []
    done_pts: list[MetricPoint] = []
    open_pts: list[MetricPoint] = []
    overdue_pts: list[MetricPoint] = []
    completion_pts: list[MetricPoint] = []
    progress_pts: list[MetricPoint] = []
    active_pts: list[MetricPoint] = []
    status_pts: list[MetricPoint] = []
    person_pts: list[MetricPoint] = []
    milestone_pts: list[MetricPoint] = []

    # Le stock ouvert est calculé depuis l'époque (cumul absolu, comme les
    # abonnés sociaux) ; le résultat ne dépend donc pas de la fenêtre demandée.
    backlog = INITIAL_BACKLOG
    for day in _days(CREATION_EPOCH, today):
        created = round(daily_value(seed, _CREATED_CONFIG, day))
        done = round(daily_value(seed, _DONE_CONFIG, day))
        backlog = round(backlog + created - done)
        if day < start:
            continue

        at = datetime.combine(day, time.min, tzinfo=UTC)
        overdue = round(backlog * (0.08 + 0.06 * hash01(seed, "projects.overdue_tasks", day)))
        completion = daily_value(seed, _COMPLETION_CONFIG, day)
        progress = max(0.0, min(100.0, daily_value(seed, _PROGRESS_CONFIG, day)))
        active = round(daily_value(seed, _ACTIVE_CONFIG, day))

        created_pts.append(MetricPoint(at=at, value=created))
        done_pts.append(MetricPoint(at=at, value=done))
        open_pts.append(MetricPoint(at=at, value=backlog))
        overdue_pts.append(MetricPoint(at=at, value=overdue))
        completion_pts.append(MetricPoint(at=at, value=completion))
        progress_pts.append(MetricPoint(at=at, value=progress))
        active_pts.append(MetricPoint(at=at, value=active))
        status_pts.append(
            _distribution_point(seed, "projects.tasks_by_status", STATUSES, backlog, at)
        )
        person_pts.append(_distribution_point(seed, "projects.person_load", PERSONS, backlog, at))
        milestone_pts.append(_milestones_point(seed, day, at))

    return [
        MetricSeries(key="projects.tasks_done", unit="tasks", period=PERIOD_DAY, points=done_pts),
        MetricSeries(
            key="projects.tasks_created", unit="tasks", period=PERIOD_DAY, points=created_pts
        ),
        MetricSeries(key="projects.open_tasks", unit="tasks", period=PERIOD_DAY, points=open_pts),
        MetricSeries(
            key="projects.overdue_tasks", unit="tasks", period=PERIOD_DAY, points=overdue_pts
        ),
        MetricSeries(
            key="projects.avg_completion_time",
            unit="days",
            period=PERIOD_DAY,
            points=completion_pts,
        ),
        MetricSeries(key="projects.avg_progress", unit="%", period=PERIOD_DAY, points=progress_pts),
        MetricSeries(
            key="projects.active_projects", unit="projects", period=PERIOD_DAY, points=active_pts
        ),
        MetricSeries(
            key="projects.tasks_by_status", unit="tasks", period=PERIOD_DAY, points=status_pts
        ),
        MetricSeries(
            key="projects.person_load", unit="tasks", period=PERIOD_DAY, points=person_pts
        ),
        MetricSeries(
            key="projects.upcoming_milestones",
            unit="days",
            period=PERIOD_DAY,
            points=milestone_pts,
        ),
    ]


class MockProjectsConnector(MockConnector):
    """Démo projets & tâches : panneau cohérent (SPÉC §3). Premier réel : projet-tâches."""

    provider = "mock.projects"
    category = Module.PROJECTS

    async def sync(self, since: datetime) -> list[MetricSeries]:
        """Les séries projets & tâches du jour de `since` au jour courant."""
        if self.seed is None:
            # Défense : un connecteur de démonstration n'a de sens que seedé.
            raise RuntimeError("Un connecteur de démonstration doit être instancié avec un seed.")
        return build_projects_series(self.seed, since)


def _milestones_point(seed: int, day: date, at: datetime) -> MetricPoint:
    """Un point « jalons à venir » : le délai restant de chaque jalon en jours
    (dimensions), et leur somme en valeur (la « charge » de jalons à venir)."""
    items: list[DistributionEntry] = [
        DistributionEntry(name=milestone, value=_days_until(seed, milestone, day))
        for milestone in MILESTONES
    ]
    items.sort(key=lambda item: item["value"])
    return MetricPoint(
        at=at,
        value=round(sum(item["value"] for item in items), 2),
        dimensions={"items": items},
    )


def _days_until(seed: int, milestone: str, day: date) -> int:
    """Délai restant en jours avant un jalon (de demain à un mois, déterministe)."""
    return round(2 + 9 * hash01(seed, "projects.milestones", milestone, day))


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
