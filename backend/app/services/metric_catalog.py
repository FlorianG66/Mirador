"""Catalogue des métriques (phase 6a) : comment réduire une fenêtre à une valeur.

Comparer une métrique sur une période suppose de la réduire à une valeur unique,
et cette réduction dépend de sa nature : un **flux** s'additionne (CA, visites),
un **niveau** garde sa dernière valeur (trésorerie, abonnés, stock de tâches),
un **taux ou une durée moyenne** se moyenne. Ce catalogue est la source de vérité
de cette connaissance métier : les services (comparaison aujourd'hui, chatbot et
export PDF plus tard) la lisent ici plutôt que de la deviner.

Les clés inconnues retombent sur la somme (le cas courant) ; un test vérifie que
toutes les métriques produites par les connecteurs y figurent explicitement.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.schemas.metrics import MetricAggregation

# Niveaux : la dernière valeur de la période fait foi (stock, solde, compteur).
_LEVEL_METRIC_KEYS: frozenset[str] = frozenset(
    {
        "finance.cash",
        "finance.invoices_outstanding",
        "social.followers",
        "projects.open_tasks",
        "projects.overdue_tasks",
        "projects.active_projects",
        "projects.upcoming_milestones",
        "projects.tasks_by_status",
        "projects.person_load",
    }
)

# Taux et durées moyennes : la moyenne de la période est la valeur représentative.
_AVERAGE_METRIC_KEYS: frozenset[str] = frozenset(
    {
        "web.engagement_rate",
        "web.avg_session_duration",
        "social.engagement_rate",
        "projects.avg_completion_time",
        "projects.avg_progress",
    }
)

# Flux : somme de la période (déclarés explicitement pour que le test de
# couverture exige chaque clé des connecteurs — aucune omission silencieuse).
_FLOW_METRIC_KEYS: frozenset[str] = frozenset(
    {
        "finance.revenue",
        "finance.expenses",
        "finance.margin",
        "finance.budget",
        "finance.top_clients",
        "finance.top_suppliers",
        "web.sessions",
        "web.visitors",
        "web.pageviews",
        "web.conversions",
        "web.traffic_sources",
        "web.top_pages",
        "web.devices",
        "web.countries",
        "social.followers_growth",
        "social.impressions",
        "social.reach",
        "social.engagements",
        "social.mentions",
        "social.posts",
        "social.top_posts",
        "projects.tasks_created",
        "projects.tasks_done",
    }
)

# Catalogue complet : chaque clé connue → son agrégation (source de vérité).
METRIC_AGGREGATIONS: dict[str, MetricAggregation] = {
    **{key: MetricAggregation.LAST for key in _LEVEL_METRIC_KEYS},
    **{key: MetricAggregation.AVERAGE for key in _AVERAGE_METRIC_KEYS},
    **{key: MetricAggregation.SUM for key in _FLOW_METRIC_KEYS},
}

# Agrégation par défaut d'une clé inconnue : le flux est le cas courant.
DEFAULT_AGGREGATION = MetricAggregation.SUM


def aggregation_for(metric_key: str) -> MetricAggregation:
    """Agrégation à appliquer à une métrique sur une période (flux par défaut)."""
    return METRIC_AGGREGATIONS.get(metric_key, DEFAULT_AGGREGATION)


def reduce_values(values: Sequence[float], aggregation: MetricAggregation) -> float:
    """Réduit une fenêtre de valeurs (ordonnées chronologiquement) à une valeur.

    Partagé par la comparaison de périodes et les objectifs : une seule règle
    de réduction pour tout le produit (aucune divergence possible).
    """
    if not values:
        return 0.0
    if aggregation == MetricAggregation.LAST:
        return values[-1]
    if aggregation == MetricAggregation.AVERAGE:
        return sum(values) / len(values)
    return sum(values)
