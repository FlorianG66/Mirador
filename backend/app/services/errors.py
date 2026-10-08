"""Erreurs métier des services : un seul type, traduit en réponse problem+json."""

from __future__ import annotations


class ServiceProblem(Exception):
    """Opération refusée par un service : code HTTP et message prêts pour le routeur.

    Le service décide du refus (conflit, accès interdit...) sans dépendre de FastAPI ;
    `app.core.errors` sérialise l'exception, les routes n'ont pas de try/except.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
