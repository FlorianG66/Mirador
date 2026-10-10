"""Tests du planificateur de synchronisation (phase 4c).

Comportement attendu : la boucle exécute le travail périodiquement jusqu'à
`stop`, un échec du travail est absorbé (la boucle continue), `start`/`stop`
sont idempotents, et l'intervalle doit être strictement positif.
"""

from __future__ import annotations

import asyncio

import pytest

from app.workers.scheduler import JobScheduler


@pytest.mark.asyncio
async def test_le_travail_tourne_periodiquement() -> None:
    calls: list[int] = []
    scheduler = JobScheduler(lambda: _record(calls), interval_seconds=0.01, name="test-period")
    await scheduler.start()
    await asyncio.sleep(0.05)
    assert scheduler.running
    await scheduler.stop()

    assert len(calls) >= 3  # ~5 boucles sur 0,05 s ; une marge suffit.


@pytest.mark.asyncio
async def test_start_est_idempotent() -> None:
    calls: list[int] = []
    scheduler = JobScheduler(lambda: _record(calls), interval_seconds=0.01, name="test-start")
    await scheduler.start()
    await scheduler.start()
    assert scheduler.running
    await asyncio.sleep(0.03)
    await scheduler.stop()

    assert len(calls) >= 2


@pytest.mark.asyncio
async def test_stop_annule_la_boucle_et_est_idempotent() -> None:
    calls: list[int] = []
    scheduler = JobScheduler(lambda: _record(calls), interval_seconds=0.01, name="test-stop")
    await scheduler.start()
    await asyncio.sleep(0.03)
    await scheduler.stop()
    count_after_stop = len(calls)

    assert not scheduler.running
    await scheduler.stop()  # second arrêt : sans effet.
    await asyncio.sleep(0.03)
    assert len(calls) == count_after_stop  # plus aucun appel après l'arrêt.


@pytest.mark.asyncio
async def test_un_echec_du_travail_ne_arrete_pas_la_boucle() -> None:
    attempts: list[int] = []
    failures = {"first"}

    async def flaky() -> None:
        if failures:
            failures.pop()
            raise RuntimeError("panne volontaire")
        attempts.append(1)

    scheduler = JobScheduler(flaky, interval_seconds=0.01, name="test-flaky")
    await scheduler.start()
    await asyncio.sleep(0.03)
    assert scheduler.running  # l'échec a été absorbé, pas d'arrêt.
    await scheduler.stop()

    assert attempts  # la boucle a poursuivi après l'échec du premier tour.


def test_intervalle_strictement_positif() -> None:
    with pytest.raises(ValueError):
        JobScheduler(lambda: asyncio.sleep(0), interval_seconds=0, name="test-zero")
    with pytest.raises(ValueError):
        JobScheduler(lambda: asyncio.sleep(0), interval_seconds=-1, name="test-neg")


async def _record(calls: list[int]) -> None:
    """Travail de test : enregistre un appel puis rend la main (sans attendre)."""
    calls.append(1)
