"""Table `legal_profiles` : fiche légale d'une organisation (SPEC §3, §5.3).

Une ligne par organisation. Chaque champ mémorise sa provenance et sa date de
synchronisation dans `field_sources` (source `registry` ou `manual`, SPEC §5.4) :
la saisie manuelle prime sur le registre, qui n'écrase jamais une valeur saisie.
Les champs de registre sont nullables — un registre ouvert est incomplet, et une
entreprise « non diffusible » n'expose ni adresse ni dirigeants.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Champs texte simples de la fiche : une seule liste, partagée avec le service.
LEGAL_PROFILE_TEXT_FIELDS: tuple[str, ...] = (
    "siret_siege",
    "raison_sociale",
    "nom_commercial",
    "forme_juridique",
    "code_naf",
    "libelle_naf",
    "adresse_siege",
    "tranche_effectif",
    "capital_social",
    "rcs_greffe",
)
# Tous les champs suivis champ par champ (source + date) dans `field_sources`.
LEGAL_PROFILE_FIELDS: tuple[str, ...] = ("siren", *LEGAL_PROFILE_TEXT_FIELDS, "date_creation")


class LegalProfile(Base):
    """Fiche légale d'une organisation : identité, fiscalité et saisie manuelle."""

    __tablename__ = "legal_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    siren: Mapped[str | None] = mapped_column(Text, nullable=True)
    siret_siege: Mapped[str | None] = mapped_column(Text, nullable=True)
    raison_sociale: Mapped[str | None] = mapped_column(Text, nullable=True)
    nom_commercial: Mapped[str | None] = mapped_column(Text, nullable=True)
    forme_juridique: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_creation: Mapped[date | None] = mapped_column(Date, nullable=True)
    code_naf: Mapped[str | None] = mapped_column(Text, nullable=True)
    libelle_naf: Mapped[str | None] = mapped_column(Text, nullable=True)
    adresse_siege: Mapped[str | None] = mapped_column(Text, nullable=True)
    tranche_effectif: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Champs de saisie manuelle fréquents (SPEC §3) : jamais fournis par le registre.
    capital_social: Mapped[str | None] = mapped_column(Text, nullable=True)
    rcs_greffe: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Dirigeants (nom + qualité) : données personnelles, masquées hors admin (SPEC §3).
    dirigeants: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    # `{champ: {"source": "registry"|"manual", "synced_at": "<iso>"}}` (SPEC §5.4).
    field_sources: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
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

    __table_args__ = (UniqueConstraint("organization_id", name="legal_profiles_organization"),)
