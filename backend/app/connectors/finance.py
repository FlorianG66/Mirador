"""Panneau financier de démonstration (sous-phase 5a, SPÉC §3 « Finance »).

Un petit écosystème cohérent et déterministe par seed : le chiffre d'affaires et
les dépenses produisent tout le reste — marge (différence), trésorerie (cumul),
budget (cible), factures impayées (niveau + ancienneté) et top clients /
fournisseurs (concentration agrégée dans les dimensions JSONB du point).

Aucune vraie entreprise ici (AGENTS.md §5) : les noms de clients et fournisseurs
sont fictifs et générés par le seed, comme toutes les valeurs.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta

from app.connectors.mock import (
    CREATION_EPOCH,
    MockConnector,
    MockMetricConfig,
    build_series,
    daily_value,
    hash01,
)
from app.models.enums import Module
from app.schemas.metrics import PERIOD_DAY, MetricPoint, MetricSeries

# Configurations de base (spirale CA → tout le reste). Le CA et les dépenses
# portent la saisonnalité, le week-end et les anomalies ; les dérivées héritent.
REVENUE = MockMetricConfig(
    key="finance.revenue",
    unit="EUR",
    base=42_000,
    trend=0.12,
    seasonality=0.15,
    weekend_factor=0.55,
    noise=0.06,
    decimals=2,
)
EXPENSES = MockMetricConfig(
    key="finance.expenses",
    unit="EUR",
    base=26_000,
    trend=0.10,
    seasonality=0.12,
    weekend_factor=0.62,
    noise=0.07,
    decimals=2,
)
BUDGET = MockMetricConfig(
    key="finance.budget",
    unit="EUR",
    base=40_000,
    trend=0.12,
    seasonality=0.10,
    weekend_factor=1.0,
    noise=0.01,
    decimals=2,
    # Une cible reste lisse : pas d'anomalie quotidienne.
    anomalies=False,
)
INVOICES = MockMetricConfig(
    key="finance.invoices_outstanding",
    unit="invoices",
    base=14,
    trend=-0.05,
    seasonality=0.10,
    weekend_factor=1.0,
    noise=0.12,
    decimals=0,
)

# Assise de trésorerie au 1er janvier 2020 (fictive), avant le premier encaissement.
OPENING_CASH = 150_000.0
# Part du CA apportée par les 5 premiers clients, du montant des dépenses vers
# les 4 principaux fournisseurs (concentration réaliste d'une TPE/PME).
TOP_CLIENT_SHARE = 0.55
TOP_SUPPLIER_SHARE = 0.40

# Portefeuilles fictifs : noms inventés, sans lien avec de vraies entreprises.
FICTIONAL_CLIENTS: tuple[str, ...] = (
    "Maison Verte",
    "Aperto Studio",
    "Nordik Énergie",
    "Plate & Co",
    "Vertex Logistique",
    "Coloris SAS",
    "Hexa Transports",
    "Mira Design",
    "Alto Digital",
    "Onyx Bâtiment",
    "Ferry Automobiles",
    "Lumen Santé",
    "Presto Services",
    "Atlas Agro",
    "Riviera Hôtels",
    "Qbit Data",
    "Zénith Mode",
    "Calida Pharma",
    "Ton & Mat",
    "Solstice Voyages",
)
FICTIONAL_SUPPLIERS: tuple[str, ...] = (
    "Matières Premières SA",
    "Atsuo Composants",
    "Papier & Flux",
    "Energie Plus",
    "Translog FR",
    "Negoce Ardent",
    "Sotral Distribution",
    "Emballo Pro",
    "Réseau Elec",
    "Bureau Direct",
    "Service Logistics",
    "Print Express",
)


def build_finance_series(seed: int, since: datetime) -> list[MetricSeries]:
    """Les séries financières du jour de `since` (borné par l'époque) à aujourd'hui.

    Les séries sont alignées jour par jour : la marge est exactement la différence
    CA − dépenses, et la trésorerie en est le cumul depuis l'époque de référence.
    """
    start = since.date()
    if start < CREATION_EPOCH:
        start = CREATION_EPOCH
    today = datetime.now(UTC).date()
    if start > today:
        return []

    clients = top_entries(seed, "finance.top_clients", FICTIONAL_CLIENTS, 5)
    suppliers = top_entries(seed, "finance.top_suppliers", FICTIONAL_SUPPLIERS, 4)

    revenue_pts: list[MetricPoint] = []
    expenses_pts: list[MetricPoint] = []
    margin_pts: list[MetricPoint] = []
    cash_pts: list[MetricPoint] = []
    top_clients_pts: list[MetricPoint] = []
    top_suppliers_pts: list[MetricPoint] = []

    # La trésorerie s'accumule depuis l'époque de référence, quelle que soit la
    # fenêtre demandée : la valeur d'un jour ne dépend que du seed et de la date.
    cash = OPENING_CASH
    for day in _days(CREATION_EPOCH, today):
        revenue = daily_value(seed, REVENUE, day)
        expenses = daily_value(seed, EXPENSES, day)
        cash += revenue - expenses
        if day < start:
            continue
        at = datetime.combine(day, time.min, tzinfo=UTC)

        revenue_pts.append(MetricPoint(at=at, value=revenue))
        expenses_pts.append(MetricPoint(at=at, value=expenses))
        margin_pts.append(MetricPoint(at=at, value=round(revenue - expenses, 2)))
        cash_pts.append(MetricPoint(at=at, value=round(cash, 2)))
        top_clients_pts.append(
            _concentration_point(
                seed, "finance.top_clients", clients, revenue, TOP_CLIENT_SHARE, at
            )
        )
        top_suppliers_pts.append(
            _concentration_point(
                seed, "finance.top_suppliers", suppliers, expenses, TOP_SUPPLIER_SHARE, at
            )
        )

    budget = build_series(seed, BUDGET, since)
    invoices = _with_aging(seed, build_series(seed, INVOICES, since))

    return [
        MetricSeries(key="finance.revenue", unit="EUR", period=PERIOD_DAY, points=revenue_pts),
        MetricSeries(key="finance.expenses", unit="EUR", period=PERIOD_DAY, points=expenses_pts),
        MetricSeries(key="finance.margin", unit="EUR", period=PERIOD_DAY, points=margin_pts),
        MetricSeries(key="finance.cash", unit="EUR", period=PERIOD_DAY, points=cash_pts),
        budget,
        invoices,
        MetricSeries(
            key="finance.top_clients",
            unit="EUR",
            period=PERIOD_DAY,
            points=top_clients_pts,
        ),
        MetricSeries(
            key="finance.top_suppliers",
            unit="EUR",
            period=PERIOD_DAY,
            points=top_suppliers_pts,
        ),
    ]


class MockFinanceConnector(MockConnector):
    """Démo finance : panneau cohérent (SPÉC §3). Premier connecteur réel : Stripe."""

    provider = "mock.finance"
    category = Module.FINANCE

    async def sync(self, since: datetime) -> list[MetricSeries]:
        """Les séries financières du jour de `since` au jour courant (voir ci-dessus)."""
        if self.seed is None:
            # Défense : un connecteur de démonstration n'a de sens que seedé.
            raise RuntimeError("Un connecteur de démonstration doit être instancié avec un seed.")
        return build_finance_series(self.seed, since)


def top_entries(seed: int, key: str, pool: tuple[str, ...], count: int) -> tuple[str, ...]:
    """Les `count` entrées du pool dont le score déterministe est le plus haut.

    Le classement est stable : un même seed donne toujours les mêmes noms, sur
    toute la période de la série (un widget « top clients » voit les mêmes noms).
    """
    ranked = sorted(pool, key=lambda name: hash01(seed, key, "rank", name), reverse=True)
    return tuple(ranked[:count])


def _concentration_point(
    seed: int,
    key: str,
    names: tuple[str, ...],
    total: float,
    share: float,
    at: datetime,
) -> MetricPoint:
    """Un point « top N » : la concentration agrégée en valeur, le détail (nom,
    montant) dans les dimensions. Poids normalisés → somme exacte = total × part."""
    weights = [_weight(seed, key, name) for name in names]
    weight_sum = sum(weights)
    amounts = [
        (name, round(total * share * weight / weight_sum, 2))
        for name, weight in zip(names, weights, strict=True)
    ]
    value = round(sum(amount for _, amount in amounts), 2)
    items = [{"name": name, "amount": amount} for name, amount in amounts]
    return MetricPoint(at=at, value=value, dimensions={"top": items})


def _weight(seed: int, key: str, name: str) -> float:
    """Poids déterministe d'un nom dans la répartition (1 × 4), normalisé ensuite."""
    return 1.0 + 3.0 * hash01(seed, key, "weight", name)


def _with_aging(seed: int, series: MetricSeries) -> MetricSeries:
    """Ajoute aux points d'impayés la répartition par ancienneté (dimensions).

    Les seuils sont stockés en jours (30/60/90+) : l'UI annonce le libellé selon
    la langue, et la somme des seaux vaut exactement le nombre d'impayés.
    """
    aged = []
    for point in series.points:
        share_open = 0.35 + 0.25 * hash01(seed, "invoices", "aging", "open")
        share_recent = 0.20 + 0.20 * hash01(seed, "invoices", "aging", "recent")
        count_open = round(point.value * share_open)
        count_recent = round(point.value * share_recent)
        aged.append(
            MetricPoint(
                at=point.at,
                value=point.value,
                dimensions={
                    "aging": [
                        {"days": 30, "count": count_open},
                        {"days": 60, "count": count_recent},
                        {"days": 90, "count": int(point.value) - count_open - count_recent},
                    ]
                },
            )
        )
    return MetricSeries(key=series.key, unit=series.unit, period=series.period, points=aged)


def _days(start: date, end: date) -> Iterator[date]:
    """Itère sur les jours inclus entre `start` et `end`."""
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)
