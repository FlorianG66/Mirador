"""Table `dashboard_layouts` : mise en page du tableau de bord par utilisateur (SPEC §4).

Un tableau de bord est personnel : chaque membre range comme il veut les widgets
de la page d'accueil (KPI clés, santé d'exploitation, objectifs, activité) et sa
disposition est mémorisée pour lui seul, dans son organisation. La table porte donc
une ligne par couple `(organization_id, user_id)` — contrainte d'unicité — et
stocke la disposition en JSONB (`widgets`) : une liste de placements
`{widget_id, x, y, w, h}` sur une grille à 12 colonnes.

Aucun libellé ni règle de rendu n'est stocké ici : le catalogue des widgets et la
disposition par défaut vivent dans `app.services.dashboard`, le frontend traduit
(AGENTS.md §7).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DashboardLayout(Base):
    """Disposition personnelle du tableau de bord d'un membre dans une organisation."""

    __tablename__ = "dashboard_layouts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # La mise en page suit l'utilisateur : elle lui est propre, dans son organisation.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Liste de placements `{widget_id, x, y, w, h}` (le type réel est JSONB).
    widgets: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="dashboard_layouts_org_user"),
        CheckConstraint("jsonb_typeof(widgets) = 'array'", name="dashboard_layouts_widgets_array"),
    )
