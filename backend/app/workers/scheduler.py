"""Planificateur asynchrone : exécute un travail à intervalles réguliers (phase 4c).

Une boucle asyncio légère lancée par le lifespan de l'application : `start`
spawn la tâche, `stop` l'annule proprement. Un échec du travail est journalisé
sans arrêter la boucle. `interval_seconds` est strictement positif.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class JobScheduler:
    """Scheduler minimal : une coroutine sans argument, un intervalle en secondes."""

    def __init__(
        self,
        job: Callable[[], Awaitable[None]],
        *,
        interval_seconds: float,
        name: str = "job",
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds doit être strictement positif")
        self._job = job
        self._interval_seconds = interval_seconds
        self._name = name
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        """Vrai tant que la boucle n'a ni fini ni été annulée."""
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Lance la boucle en arrière-plan ; sans effet si elle tourne déjà."""
        if self.running:
            return
        self._task = asyncio.create_task(self._loop(), name=f"mirador-{self._name}")
        logger.info(
            "Planificateur « %s » démarré (intervalle %ss)",
            self._name,
            self._interval_seconds,
        )

    async def stop(self) -> None:
        """Annule la boucle ; relançable par `start`. Idempotent."""
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Planificateur « %s » arrêté", self._name)

    async def _loop(self) -> None:
        while True:
            try:
                await self._job()
            except Exception:
                logger.exception("Travail « %s » en échec : la boucle continue", self._name)
            await asyncio.sleep(self._interval_seconds)
