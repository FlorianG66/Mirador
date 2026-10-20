"""Règles d'alerte configurables (SPEC §4) : seuil franchi sur une métrique.

Une règle surveille une clé canonique sur une fenêtre glissante (`period_days`) et
se déclenche quand la valeur agrégée franchit `threshold` dans le sens
`comparison` (`above` = au-dessus, `below` = en dessous). Aucun texte n'est figé
côté backend : `label` est une donnée saisie par l'utilisateur, et la notification
produite porte un `kind` (clé i18n) que le frontend traduit.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AlertComparison
from app.schemas.metrics import validate_metric_key

__all__ = [
    "AlertComparison",
    "AlertRuleCreate",
    "AlertRuleOut",
    "AlertRuleUpdate",
]


class AlertRuleCreate(BaseModel):
    """Définition d'une règle d'alerte à créer (seuil sur une clé canonique)."""

    metric_key: str
    label: str | None = Field(default=None, max_length=120)
    comparison: AlertComparison = AlertComparison.ABOVE
    threshold: float
    period_days: int = Field(default=1, ge=1, le=365)
    enabled: bool = True

    @field_validator("metric_key")
    @classmethod
    def _key_is_canonical(cls, value: str) -> str:
        return validate_metric_key(value)


class AlertRuleUpdate(BaseModel):
    """Mise à jour partielle : seuls les champs fournis sont modifiés.

    Un `label` explicitement `null` efface le libellé (retour au libellé i18n de
    la métrique côté interface) ; un champ omis garde sa valeur.
    """

    metric_key: str | None = None
    label: str | None = Field(default=None, max_length=120)
    comparison: AlertComparison | None = None
    threshold: float | None = None
    period_days: int | None = Field(default=None, ge=1, le=365)
    enabled: bool | None = None

    @field_validator("metric_key")
    @classmethod
    def _key_is_canonical(cls, value: str | None) -> str | None:
        return validate_metric_key(value) if value is not None else None


class AlertRuleOut(BaseModel):
    """Règle d'alerte complète : définition + horodatages."""

    id: uuid.UUID
    metric_key: str
    label: str | None
    comparison: AlertComparison
    threshold: float
    period_days: int
    enabled: bool
    created_at: datetime
    updated_at: datetime
