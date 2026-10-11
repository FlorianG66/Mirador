"""Table `legal_identifiers` : identifiants légaux génériques par pays (SPEC §5.3).

Schéma ouvert à d'autres pays que la France plus tard : `(pays, schéma, valeur)`.
Le MVP n'y range que le numéro de TVA intracommunautaire (schéma `vat`), calculé
depuis le SIREN puis, à terme, vérifié via VIES. `source` distingue une valeur de
registre, saisie à la main ou calculée ; `verified_at` reste nul tant que la
vérification externe (VIES) n'a pas eu lieu.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Schémas d'identifiants connus du MVP (le schéma est un texte libre côté base).
IDENTIFIER_SCHEMA_VAT = "vat"


class LegalIdentifier(Base):
    """Un identifiant légal d'une organisation, par pays et par schéma."""

    __tablename__ = "legal_identifiers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Code pays ISO 3166-1 alpha-2 (SPEC §5.4 : France d'abord).
    pays: Mapped[str] = mapped_column(String(2), nullable=False)
    schema: Mapped[str] = mapped_column(Text, nullable=False)
    valeur: Mapped[str] = mapped_column(Text, nullable=False)
    # `registry` | `manual` | `computed` (SPEC §5.4).
    source: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        UniqueConstraint(
            "organization_id", "pays", "schema", name="legal_identifiers_org_pays_schema"
        ),
    )
