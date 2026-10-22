"""Table `organizations` : l'établissement rattaché à un compte (SPEC §2)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import DEMO_SECTOR_VALUES_SQL

# Un SIREN compte 9 chiffres ; la clé de Luhn est vérifiée côté applicatif (SPEC §5.4).
SIREN_DIGITS = 9


class Organization(Base):
    """Un établissement : propriétaire de toutes les données métier (`organization_id`)."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Champ optionnel (SPEC §2) : renseigné à l'inscription, jamais exigé.
    siren: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Organisation de démonstration (SPEC §9) : fictive, isolée et réinitialisable.
    is_demo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    demo_sector: Mapped[str | None] = mapped_column(Text, nullable=True)
    demo_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        CheckConstraint(
            f"siren IS NULL OR (siren ~ '^[0-9]{{{SIREN_DIGITS}}}$')",
            name="organizations_siren_format",
        ),
        # Une démo a toujours un secteur connu et une échéance ; une vraie organisation
        # n'en porte aucune trace. La cohérence est ainsi garantie par la base.
        CheckConstraint(
            "(NOT is_demo AND demo_sector IS NULL AND demo_expires_at IS NULL)"
            f" OR (is_demo AND demo_sector IN ({DEMO_SECTOR_VALUES_SQL})"
            " AND demo_expires_at IS NOT NULL)",
            name="organizations_demo_fields",
        ),
        Index(
            "ix_organizations_demo_expires_at",
            "demo_expires_at",
            postgresql_where=text("is_demo"),
        ),
    )
