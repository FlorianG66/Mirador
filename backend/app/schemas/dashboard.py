"""Tableau de bord personnalisable (SPEC §4) : catalogue de widgets et mise en page.

Le backend ne compose aucun libellé (AGENTS.md §7) : il renvoie l'identifiant du
widget, son genre et, pour un KPI, la clé canonique et le module. Le frontend
traduit et rend le composant correspondant. Une mise en page valide respecte une
grille de 12 colonnes : `x + w ≤ 12`, largeur et hauteur bornées.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.models.enums import Module

# Largeur de la grille du tableau de bord (colonnes), partagée avec react-grid-layout.
GRID_COLUMNS = 12
# Bornes de hauteur d'un widget, en unités de ligne de la grille.
MAX_WIDGET_HEIGHT = 24
# Nombre maximal de widgets dans une mise en page (borne de sécurité).
MAX_WIDGETS = 24


class WidgetKind(StrEnum):
    """Genre d'un widget : détermine le composant frontend qui le rend."""

    HEALTH = "health"
    GOALS = "goals"
    ACTIVITY = "activity"
    KPI = "kpi"


class DashboardWidgetOut(BaseModel):
    """Entrée du catalogue : de quoi identifier et rendre un widget."""

    widget_id: str
    kind: WidgetKind
    module: Module | None = None
    metric_key: str | None = None


class DashboardPlacement(BaseModel):
    """Placement d'un widget sur la grille (coin haut-gauche, largeur, hauteur)."""

    widget_id: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(ge=1, le=GRID_COLUMNS)
    h: int = Field(ge=1, le=MAX_WIDGET_HEIGHT)

    @model_validator(mode="after")
    def _within_grid(self) -> Self:
        """Refuse un widget qui déborde de la grille (x + w > nombre de colonnes)."""
        if self.x + self.w > GRID_COLUMNS:
            raise ValueError("Le widget dépasse la largeur de la grille (x + w > 12).")
        return self


class DashboardLayoutUpdate(BaseModel):
    """Corps du PUT : la liste complète des placements, sans doublon."""

    widgets: list[DashboardPlacement] = Field(default_factory=list, max_length=MAX_WIDGETS)

    @model_validator(mode="after")
    def _no_duplicate(self) -> Self:
        """Un même widget ne peut être placé qu'une fois."""
        widget_ids = [placement.widget_id for placement in self.widgets]
        if len(set(widget_ids)) != len(widget_ids):
            raise ValueError("Un widget ne peut apparaître qu'une fois dans la mise en page.")
        return self


class DashboardOut(BaseModel):
    """Mise en page courante + catalogue des widgets autorisés pour le membre."""

    available_widgets: list[DashboardWidgetOut]
    layout: list[DashboardPlacement]
    is_default: bool
