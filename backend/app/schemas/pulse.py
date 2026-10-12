"""Pouls (phase 5f) : agrégat de la page d'accueil, tous modules confondus.

Le backend ne compose aucun libellé : il renvoie la clé canonique et la valeur,
le frontend les traduit (AGENTS.md §7). La même structure sert de contrat unique
pour les KPI clés, l'indicateur de santé et le fil d'activité.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import Module
from app.schemas.team import AuditLogOut


class PulseKpiOut(BaseModel):
    """Dernière valeur d'un KPI clé, avec la valeur précédente pour la tendance."""

    module: Module
    metric_key: str
    unit: str
    value: float
    previous_value: float | None = None
    captured_at: datetime


class PulseHealthOut(BaseModel):
    """Santé opérationnelle : modules alimentés sur les modules autorisés.

    Un module sans donnée signifie « pas encore connecté » (démo non
    synchronisée) : c'est un signal d'exploitation, pas un jugement financier
    (les règles d'alerte métier arrivent en phase 6).
    """

    status: Literal["good", "warning", "unknown"]
    modules_with_data: int
    modules_total: int


class PulseOut(BaseModel):
    """Réponse du Pouls : KPI clés, santé et fil d'activité (réservé aux admins)."""

    kpis: list[PulseKpiOut] = Field(default_factory=list)
    health: PulseHealthOut
    activity: list[AuditLogOut] = Field(default_factory=list)
