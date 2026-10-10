"""Interface `Connector` : contrat commun à tout connecteur de données (SPEC §5.4).

Un connecteur expose son `provider`, sa `category` et son `auth_type`, et produit
des séquences de métriques canoniques (`MetricSeries`) par `sync` ou par webhook.
Le format réel/mock est identique : basculer de l'un à l'autre ne change rien au
reste de l'application.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.models.enums import Module
from app.schemas.metrics import MetricSeries


class ConnectorHealth(BaseModel):
    """État déclaré par un connecteur (self-description pour l'UI)."""

    status: Literal["ok", "degraded", "error"]
    latency_ms: int = 0
    message: str = ""


class Connector(ABC):
    """Un fournisseur de données produit des métriques canoniques (SPEC §5.4).

    Les champs `provider`, `category` et `auth_type` sont des attributs de classe
    : ils décrivent le connecteur, pas une instance (un mock est partagé par seed).
    """

    provider: str
    category: Module
    auth_type: str

    def __init__(self, seed: int | None = None) -> None:
        """Un connecteur de démonstration est paramétré par un seed déterministe ;
        un connecteur réel ignorera ce paramètre (ses jetons viennent du service)."""
        self.seed = seed

    @abstractmethod
    async def connect(self) -> None:
        """Établit la session avec le fournisseur (jetons, handshake OAuth…)."""

    @abstractmethod
    async def sync(self, since: datetime) -> list[MetricSeries]:
        """Retourne les séries de métriques des points postérieurs à `since`."""

    @abstractmethod
    async def handle_webhook(self, payload: dict[str, Any]) -> list[MetricSeries]:
        """Traite un webhook entrant (push) et retourne les métriques correspondantes."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Ferme la session et nettoie les ressources éventuelles."""

    @abstractmethod
    async def healthcheck(self) -> ConnectorHealth:
        """État de santé du connecteur (utilisé par l'UI et les alertes)."""
