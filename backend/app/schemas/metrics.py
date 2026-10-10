"""Métriques canoniques (SPEC §5.4) : le format partagé par tout connecteur,
réel ou mock, et par l'API de lecture. Clé `module.metric` (ex. `finance.revenue`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Module

# Durée ISO 8601 d'un pas de série de démonstration (SPÉC §5.4).
PERIOD_DAY = "P1D"
# Permet aux règles métier de raisonner sur les clés et leurs préfixes de module.
METRIC_KEY_SEPARATOR = "."


class MetricPoint(BaseModel):
    """Un point d'une série : un instant, une valeur, éventuellement des dimensions."""

    at: datetime
    value: float
    dimensions: dict[str, Any] = Field(default_factory=dict)


class MetricSeries(BaseModel):
    """Série canonique : clé, unité, période et points (format identique réel/mock)."""

    key: str
    unit: str = Field(min_length=1, max_length=16)
    period: str = Field(min_length=1, max_length=8)
    points: list[MetricPoint] = Field(default_factory=list)

    @field_validator("key")
    @classmethod
    def _key_is_canonical(cls, value: str) -> str:
        """Exige la forme `module.metric` avec un module connu (SPEC §5.4)."""
        module, sep, metric = value.partition(METRIC_KEY_SEPARATOR)
        if not sep:
            raise ValueError("Clé non canonique : « module.metric » attendu (ex. finance.revenue)")
        if not metric or METRIC_KEY_SEPARATOR in metric or METRIC_KEY_SEPARATOR in module:
            raise ValueError("Clé non canonique : un seul séparateur « . » autorisé")
        try:
            Module(module)
        except ValueError as exc:
            raise ValueError(f"Module inconnu dans la clé : « {module} »") from exc
        return value


def metric_prefix(key: str) -> str:
    """Préfixe `module` d'une clé canonique (pour les permissions et le filtrage)."""
    return key.partition(METRIC_KEY_SEPARATOR)[0]


def build_metric_key(module: Module, metric: str) -> str:
    """Construit une clé canonique à partir d'un module et d'un nom de métrique."""
    return f"{module.value}{METRIC_KEY_SEPARATOR}{metric}"
