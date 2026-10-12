"""Table `goals` : objectifs et budgets sur n'importe quel KPI (SPEC §4).

Un objectif porte trois choix et une cible : la **clé canonique** visée, le **sens**
(`at_least` = atteindre au moins la cible, `at_most` = rester en dessous, cas du
budget), la **valeur cible** et la **fenêtre glissante** (`period_days`) sur
laquelle la métrique est agrégée. La progression et l'alerte de dérive ne sont
pas stockées : elles se recalculent à la lecture (le service les dérive des
`metric_snapshots` et du catalogue d'agrégation).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Double, ForeignKey, Integer, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import GOAL_DIRECTION_VALUES_SQL
from app.models.metric_snapshot import METRIC_KEY_REGEX


class Goal(Base):
    """Un objectif (ou budget) d'une organisation sur une métrique canonique."""

    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_key: Mapped[str] = mapped_column(Text, nullable=False)
    # Libellé libre saisi par l'utilisateur (donnée, pas texte d'interface) ; vide par
    # défaut : l'interface affiche alors le libellé i18n de la métrique (SPEC §7).
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    target_value: Mapped[float] = mapped_column(Double, nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
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
        CheckConstraint(f"metric_key ~ '{METRIC_KEY_REGEX}'", name="goals_key_format"),
        CheckConstraint(
            f"direction IN ({GOAL_DIRECTION_VALUES_SQL})", name="goals_direction_known"
        ),
        CheckConstraint("period_days BETWEEN 1 AND 365", name="goals_period_days_range"),
    )
