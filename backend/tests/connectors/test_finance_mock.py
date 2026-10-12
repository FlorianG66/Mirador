"""Tests du panneau financier de démonstration (sous-phase 5a, SPÉC §3).

Vérifie la cohérence d'ensemble (marge = CA − dépenses, trésorerie = cumul), la
stabilité selon la fenêtre demandée, les dimensions (ancienneté des impayés, top
clients/fournisseurs) et le déterminisme par seed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.connectors import registry
from app.connectors.finance import (
    CREATION_EPOCH,
    OPENING_CASH,
    TOP_CLIENT_SHARE,
    build_finance_series,
)

_NOW = datetime.now(UTC)
_WINDOW = timedelta(days=84)

FINANCE_KEYS = {
    "finance.revenue",
    "finance.expenses",
    "finance.margin",
    "finance.cash",
    "finance.budget",
    "finance.invoices_outstanding",
    "finance.top_clients",
    "finance.top_suppliers",
}


def _points(seed: int, since: datetime | None = None):
    """Séries financières indexées par clé, sur la fenêtre standard sauf précision."""
    returned = build_finance_series(seed, since or _NOW - _WINDOW)
    return {series.key: series.points for series in returned}


def test_le_panneau_contient_les_huit_series_attendues() -> None:
    by_key = _points(42)
    assert set(by_key) == FINANCE_KEYS
    assert all(by_key[key] and by_key[key][0].at.tzinfo == UTC for key in by_key)


def test_marge_est_la_difference_ca_depenses() -> None:
    by_key = _points(7)
    revenue = by_key["finance.revenue"]
    expenses = by_key["finance.expenses"]
    margin = by_key["finance.margin"]
    assert [p.at for p in margin] == [p.at for p in revenue]
    for rev, exp, marg in zip(revenue, expenses, margin, strict=True):
        assert marg.value == round(rev.value - exp.value, 2)


def test_tresorerie_est_le_cumul_du_ca_moins_les_depenses() -> None:
    by_key = _points(7)
    revenue = by_key["finance.revenue"]
    expenses = by_key["finance.expenses"]
    cash = by_key["finance.cash"]
    assert [p.at for p in cash] == [p.at for p in revenue]
    # Récurrence d'un jour à l'autre : la trésorerie absorbe le net du jour j+1
    # (arrondis au centime près). Alignement : cash[j+1] − cash[j] == net[j+1].
    for previous, current, rev, exp in zip(cash, cash[1:], revenue[1:], expenses[1:], strict=False):
        expected = previous.value + rev.value - exp.value
        assert current.value == pytest.approx(expected, abs=0.05)


def test_tresorerie_sur_la_fenetre_entiere_depart_plus_net() -> None:
    by_key = _points(7, datetime.combine(CREATION_EPOCH, datetime.min.time(), tzinfo=UTC))
    revenue = by_key["finance.revenue"]
    expenses = by_key["finance.expenses"]
    cash = by_key["finance.cash"]
    assert cash[0].value == pytest.approx(
        OPENING_CASH + revenue[0].value - expenses[0].value, abs=0.05
    )


def test_tresorerie_ne_depend_pas_de_la_fenetre_demandee() -> None:
    recent = _points(7, _NOW - timedelta(days=14))
    long = _points(7, _NOW - timedelta(days=200))
    assert recent["finance.cash"][-1].value == long["finance.cash"][-1].value


def test_top_clients_concentration_et_noms_stables() -> None:
    by_key = _points(11)
    top_clients = by_key["finance.top_clients"]
    revenue = by_key["finance.revenue"]

    names_by_point = {
        tuple(item["name"] for item in point.dimensions["top"]) for point in top_clients
    }
    assert len(names_by_point) == 1  # les mêmes noms sur toute la période

    for point, rev in zip(top_clients, revenue, strict=True):
        amounts = [item["amount"] for item in point.dimensions["top"]]
        assert len(amounts) == 5
        assert all(amount > 0 for amount in amounts)
        assert point.value == round(sum(amounts), 2)
        # La concentration est exactement la part visée du CA (arrondis au centime près).
        assert point.value == pytest.approx(rev.value * TOP_CLIENT_SHARE, abs=0.05)


def test_top_fournisseurs_sur_les_depenses() -> None:
    top_suppliers = _points(11)["finance.top_suppliers"]
    for point in top_suppliers:
        amounts = [item["amount"] for item in point.dimensions["top"]]
        assert len(amounts) == 4
        assert point.value == round(sum(amounts), 2)


def test_impayes_anciennete_somme_exacte() -> None:
    invoices = _points(13)["finance.invoices_outstanding"]
    for point in invoices:
        aging = point.dimensions["aging"]
        assert [bucket["days"] for bucket in aging] == [30, 60, 90]
        assert sum(bucket["count"] for bucket in aging) == int(point.value)
        assert all(bucket["count"] >= 0 for bucket in aging)


def test_budget_est_une_cible_lisse_et_positive() -> None:
    by_key = _points(5)
    budget = by_key["finance.budget"]
    values = [point.value for point in budget]
    assert all(value > 0 for value in values)
    # Bruit limité (1 %) : la cible ne fait pas de sauts d'un jour à l'autre.
    assert max(values) / min(values) < 1.5


def test_le_seed_change_le_panneau_mais_pas_sa_structure() -> None:
    seed_a = _points(1)
    seed_b = _points(2)
    assert set(seed_a) == set(seed_b)
    assert [p.value for p in seed_a["finance.cash"]] != [p.value for p in seed_b["finance.cash"]]


@pytest.mark.asyncio
async def test_sync_deterministe_et_futur_vide() -> None:
    future = _NOW + timedelta(days=1)
    connector = registry.make("mock.finance", seed=9)
    assert await connector.sync(future) == []
    series = await connector.sync(_NOW - _WINDOW)
    assert {metric.key for metric in series} == FINANCE_KEYS
