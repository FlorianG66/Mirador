"""Objectifs et budgets (SPEC §4) : cible sur n'importe quel KPI, progression, alerte.

La progression n'est pas une donnée stockée : elle se dérive à la lecture de la
métrique visée. Le service renvoie donc, à côté de la définition de l'objectif,
un bloc `progress` (valeur courante, valeur précédente équivalente, pourcentage
et statut). `direction` vient de `app.models.enums` pour rester la même source de
vérité que la contrainte de base.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.models.enums import GoalDirection
from app.schemas.metrics import validate_metric_key

__all__ = [
    "GoalCreate",
    "GoalDirection",
    "GoalOut",
    "GoalProgress",
    "GoalStatus",
    "GoalUpdate",
]


class GoalStatus(StrEnum):
    """État d'un objectif, calculé à la lecture (jamais stocké).

    - `achieved` : la cible est atteinte.
    - `off_track` : la cible n'est pas atteinte **et** la métrique s'en éloigne
      (dérive par rapport à la fenêtre précédente équivalente).
    - `on_track` : la cible n'est pas encore atteinte mais la métrique progresse
      ou se maintient.
    - `unknown` : aucune donnée sur la fenêtre (module pas encore synchronisé).
    """

    ACHIEVED = "achieved"
    ON_TRACK = "on_track"
    OFF_TRACK = "off_track"
    UNKNOWN = "unknown"


class GoalCreate(BaseModel):
    """Définition d'un objectif à créer (cible sur une clé canonique)."""

    metric_key: str
    label: str | None = Field(default=None, max_length=120)
    direction: GoalDirection = GoalDirection.AT_LEAST
    target_value: float
    period_days: int = Field(default=30, ge=1, le=365)

    @field_validator("metric_key")
    @classmethod
    def _key_is_canonical(cls, value: str) -> str:
        return validate_metric_key(value)


class GoalUpdate(BaseModel):
    """Mise à jour partielle : seuls les champs fournis sont modifiés.

    Un `label` explicitement `null` efface le libellé (retour au libellé i18n de
    la métrique côté interface) ; un champ omis garde sa valeur.
    """

    metric_key: str | None = None
    label: str | None = Field(default=None, max_length=120)
    direction: GoalDirection | None = None
    target_value: float | None = None
    period_days: int | None = Field(default=None, ge=1, le=365)

    @field_validator("metric_key")
    @classmethod
    def _key_is_canonical(cls, value: str | None) -> str | None:
        return validate_metric_key(value) if value is not None else None


class GoalProgress(BaseModel):
    """Progression recalculée d'un objectif sur sa fenêtre glissante.

    `current_value` est agrégée selon le catalogue de métriques (somme pour un
    flux, dernière valeur pour un niveau, moyenne pour un taux). `progress_percent`
    peut dépasser 100 (cible dépassée) et vaut `None` si la cible est nulle.
    """

    current_value: float | None = None
    previous_value: float | None = None
    progress_percent: float | None = None
    status: GoalStatus = GoalStatus.UNKNOWN
    unit: str | None = None


class GoalOut(GoalCreate):
    """Objectif complet : définition + progression calculée + horodatages."""

    id: uuid.UUID
    progress: GoalProgress
    created_at: datetime
    updated_at: datetime
