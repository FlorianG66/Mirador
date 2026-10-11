"""Tests du panneau projets & tâches de démonstration (sous-phase 5d, SPÉC §3).

Vérifie la cohérence d'ensemble (tâches ouvertes = différence cumulée entre
créées et terminées, retards ≤ stock ouvert), les répartitions (par statut et
par personne, qui somment exactement leur métrique parente), les jalons à venir
(dans un futur proche, leur somme vaut le total de la série), le réalisme et le
déterminisme par seed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.connectors import registry
from app.connectors.projects import (
    MILESTONES,
    PERSONS,
    STATUSES,
    build_projects_series,
)

_NOW = datetime.now(UTC)
_WINDOW = timedelta(days=84)

PROJECT_KEYS = {
    "projects.active_projects",
    "projects.avg_completion_time",
    "projects.avg_progress",
    "projects.open_tasks",
    "projects.overdue_tasks",
    "projects.person_load",
    "projects.tasks_by_status",
    "projects.tasks_created",
    "projects.tasks_done",
    "projects.upcoming_milestones",
}


def _by_key(seed: int, since: datetime | None = None):
    """Séries projets indexées par clé, sur la fenêtre standard sauf précision."""
    returned = build_projects_series(seed, since or _NOW - _WINDOW)
    return {series.key: series.points for series in returned}


def test_le_panneau_contient_les_dix_series_attendues() -> None:
    by_key = _by_key(42)
    assert set(by_key) == PROJECT_KEYS
    assert all(by_key[key] and by_key[key][0].at.tzinfo == UTC for key in by_key)
    assert all(len(by_key[key]) == len(by_key["projects.tasks_done"]) for key in by_key)


def test_taches_crees_en_moyenne_superieures_aux_terminees() -> None:
    # Le rétroplanning fictif grossit : en moyenne plus de créées que de
    # terminées, ce qui alimente le stock de tâches ouvertes.
    by_key = _by_key(42, _NOW - timedelta(days=365))
    created = [p.value for p in by_key["projects.tasks_created"]]
    done = [p.value for p in by_key["projects.tasks_done"]]
    assert all(value >= 0 for value in done)
    assert sum(created) / len(created) > sum(done) / len(done)


def test_ouvert_est_la_difference_cumulee_au_quotidien() -> None:
    by_key = _by_key(42)
    opened = by_key["projects.open_tasks"]
    created = by_key["projects.tasks_created"]
    done = by_key["projects.tasks_done"]
    assert all(point.value >= 0 for point in opened)
    for index in range(1, len(opened)):
        delta = opened[index].value - opened[index - 1].value
        assert delta == pytest.approx(created[index].value - done[index].value, abs=0.01)


def test_retards_ne_depassent_jamais_le_stock_ouvert() -> None:
    by_key = _by_key(42)
    for opened, overdue in zip(
        by_key["projects.open_tasks"], by_key["projects.overdue_tasks"], strict=True
    ):
        assert 0 <= overdue.value <= opened.value


def test_avancement_moyen_reste_entre_0_et_100() -> None:
    by_key = _by_key(7)
    assert all(0 <= point.value <= 100 for point in by_key["projects.avg_progress"])
    assert any(point.value > 0 for point in by_key["projects.avg_progress"])


def test_delai_moyen_de_livraison_positif_et_raisonnable() -> None:
    by_key = _by_key(7)
    assert all(1 <= point.value <= 30 for point in by_key["projects.avg_completion_time"])


def test_projets_actifs_positifs() -> None:
    by_key = _by_key(7)
    assert all(point.value >= 1 for point in by_key["projects.active_projects"])


def test_taches_par_statut_somment_les_ouvertes() -> None:
    by_key = _by_key(11)
    for status_point, opened in zip(
        by_key["projects.tasks_by_status"], by_key["projects.open_tasks"], strict=True
    ):
        items = status_point.dimensions["items"]
        assert {item["name"] for item in items} == set(STATUSES)
        assert status_point.value == round(sum(item["value"] for item in items), 2)
        assert status_point.value == pytest.approx(opened.value, abs=0.01)


def test_charge_par_personne_somme_les_ouvertes() -> None:
    by_key = _by_key(11)
    for person_point, opened in zip(
        by_key["projects.person_load"], by_key["projects.open_tasks"], strict=True
    ):
        items = person_point.dimensions["items"]
        assert {item["name"] for item in items} == set(PERSONS)
        assert person_point.value == round(sum(item["value"] for item in items), 2)
        assert person_point.value == pytest.approx(opened.value, abs=0.01)


def test_jalons_a_venir_somment_et_sont_dans_le_futur_proche() -> None:
    by_key = _by_key(11)
    for point in by_key["projects.upcoming_milestones"]:
        items = point.dimensions["items"]
        assert {item["name"] for item in items} == set(MILESTONES)
        assert point.value == round(sum(item["value"] for item in items), 2)
        # Délais restants : au moins demain, au plus un mois.
        values = [item["value"] for item in items]
        assert values == sorted(values)
        assert all(1 <= value <= 30 for value in values)


def test_le_seed_change_les_valeurs_mais_pas_la_structure() -> None:
    seed_a = _by_key(1)
    seed_b = _by_key(2)
    assert set(seed_a) == set(seed_b)
    assert [p.value for p in seed_a["projects.overdue_tasks"]] != [
        p.value for p in seed_b["projects.overdue_tasks"]
    ]


@pytest.mark.asyncio
async def test_sync_deterministe_et_futur_vide() -> None:
    future = _NOW + timedelta(days=1)
    connector = registry.make("mock.projects", seed=9)
    assert await connector.sync(future) == []
    series = await connector.sync(_NOW - _WINDOW)
    assert {metric.key for metric in series} == PROJECT_KEYS
