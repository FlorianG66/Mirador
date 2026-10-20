"""Table `alert_rules` : règles d'alerte configurables (SPEC §4, phase 6c-iii).

Une règle surveille **une clé canonique** sur une **fenêtre glissante** et se
déclenche quand la valeur agrégée franchit un **seuil** dans un sens donné
(`above` = au-dessus, `below` = en dessous). Une primitive unique couvre les
exemples de la SPEC (seuil dépassé, facture impayée) ; « objectif atteint » reste
porté par la table `goals` (6c-ii). Comme pour les objectifs, ni l'état courant
ni l'historique des déclenchements ne sont stockés : l'évaluation lit les
`metric_snapshots` et la déduplication des notifications s'appuie sur `dedup_key`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ALERT_COMPARISON_VALUES_SQL
from app.models.metric_snapshot import METRIC_KEY_REGEX


class AlertRule(Base):
    """Une règle d'alerte d'une organisation sur une métrique canonique."""

    __tablename__ = "alert_rules"

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
    comparison: Mapped[str] = mapped_column(Text, nullable=False)
    threshold: Mapped[float] = mapped_column(Double, nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
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
        CheckConstraint(f"metric_key ~ '{METRIC_KEY_REGEX}'", name="alert_rules_key_format"),
        CheckConstraint(
            f"comparison IN ({ALERT_COMPARISON_VALUES_SQL})", name="alert_rules_comparison_known"
        ),
        CheckConstraint("period_days BETWEEN 1 AND 365", name="alert_rules_period_days_range"),
    )
