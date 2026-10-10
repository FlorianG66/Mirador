"""Table `metric_snapshots` : valeurs stockées des métriques canoniques (SPEC §5.3).

Une ligne = un point d'une série, pour une organisation : `organization_id` +
clé `module.metric` + `captured_at` (unique). Le stockage est séparé de la
production des données : les connecteurs génèrent, le worker écrit, l'API lit.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Modules qui peuvent préfixer une clé canonique (SPEC §5.4) : ordre alphabétique.
METRIC_KEY_REGEX = r"^(finance|legal|projects|social|web)\.[a-z0-9_]+$"
# Durées ISO 8601 simples (ex. P1D, P7D, P1M) — SPEC §5.4.
PERIOD_REGEX = r"^P[0-9]+(D|W|M|Y)$"


class MetricSnapshot(Base):
    """Un point d'une métrique canonique, rattaché à une organisation."""

    __tablename__ = "metric_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_key: Mapped[str] = mapped_column(Text, nullable=False)
    # Unité canonique de la série (EUR, visites, tâches…) : stockée par point pour
    # que l'endpoint de lecture soit générique (il ne connaît pas le connecteur).
    unit: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    period: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[float] = mapped_column(Double, nullable=False)
    dimensions: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Une même valeur est réécrite au lieu de dupliquée lors d'une re-synchro.
        UniqueConstraint(
            "organization_id", "metric_key", "captured_at", name="metric_snapshots_org_key_at"
        ),
        CheckConstraint(f"metric_key ~ '{METRIC_KEY_REGEX}'", name="metric_snapshots_key_format"),
        CheckConstraint(f"period ~ '{PERIOD_REGEX}'", name="metric_snapshots_period_format"),
    )
