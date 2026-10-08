"""Table `organizations` : l'établissement rattaché à un compte (SPEC §2)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

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
    )
