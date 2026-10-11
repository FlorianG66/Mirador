"""Schémas de la fiche légale (phase 5e) : lecture, mise à jour manuelle, provenance.

La fiche expose chaque champ avec sa provenance (`sources` : source + date de
synchronisation) et les identifiants génériques par pays (aujourd'hui la TVA). La
mise à jour ne porte que sur les champs explicitement présents dans le corps : un
champ omis garde sa valeur et sa source (la saisie manuelle prime, SPEC §5.4).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.core.siren import is_valid_siren, is_valid_siret
from app.models.legal_profile import LEGAL_PROFILE_TEXT_FIELDS


class FieldSourceOut(BaseModel):
    """Provenance d'un champ : registre ou saisie manuelle, à une date donnée."""

    source: str
    synced_at: datetime | None = None


class LegalDirectorOut(BaseModel):
    """Dirigeant publié au registre ou saisi : nom et qualité (donnée personnelle)."""

    nom: str
    qualite: str | None = None


class LegalIdentifierOut(BaseModel):
    """Identifiant légal générique (pays + schéma), ex. le numéro de TVA.

    Le champ est exposé en JSON sous `schema` ; en Python il porte `schema_name`
    car `schema` entre en conflit avec une méthode de `BaseModel`.
    """

    pays: str
    schema_name: str = Field(serialization_alias="schema")
    valeur: str
    source: str
    verified_at: datetime | None


class LegalProfileOut(BaseModel):
    """Fiche légale complète : identité, fiscalité, provenance et dirigeants."""

    siren: str | None
    siret_siege: str | None
    raison_sociale: str | None
    nom_commercial: str | None
    forme_juridique: str | None
    date_creation: date | None
    code_naf: str | None
    libelle_naf: str | None
    adresse_siege: str | None
    tranche_effectif: str | None
    capital_social: str | None
    rcs_greffe: str | None
    # Vide pour un membre non-admin : données personnelles masquées (SPEC §3).
    dirigeants: list[LegalDirectorOut] = Field(default_factory=list)
    sources: dict[str, FieldSourceOut] = Field(default_factory=dict)
    identifiers: list[LegalIdentifierOut] = Field(default_factory=list)
    updated_at: datetime | None = None


class LegalDirectorUpdate(BaseModel):
    """Dirigeant saisi à la main (utile quand le registre ne le publie pas)."""

    nom: str = Field(min_length=1, max_length=200)
    qualite: str | None = Field(default=None, max_length=200)


class LegalProfileUpdate(BaseModel):
    """Champs de saisie manuelle : seuls ceux fournis sont écrits (SPEC §5.4).

    Tous optionnels ; un champ absent du corps est inchangé. Le SIREN et le SIRET
    sont validés (Luhn) dès qu'ils sont fournis ; un SIREN valide recalcule la TVA.
    """

    siren: str | None = None
    siret_siege: str | None = None
    raison_sociale: str | None = Field(default=None, max_length=300)
    nom_commercial: str | None = Field(default=None, max_length=300)
    forme_juridique: str | None = Field(default=None, max_length=200)
    date_creation: date | None = None
    code_naf: str | None = Field(default=None, max_length=10)
    libelle_naf: str | None = Field(default=None, max_length=300)
    adresse_siege: str | None = Field(default=None, max_length=500)
    tranche_effectif: str | None = Field(default=None, max_length=20)
    capital_social: str | None = Field(default=None, max_length=100)
    rcs_greffe: str | None = Field(default=None, max_length=200)
    dirigeants: list[LegalDirectorUpdate] | None = None

    @field_validator("siren")
    @classmethod
    def _siren_is_valid(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_siren(value):
            raise ValueError("SIREN invalide : 9 chiffres et clé de Luhn attendus.")
        return value

    @field_validator("siret_siege")
    @classmethod
    def _siret_is_valid(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_siret(value):
            raise ValueError("SIRET invalide : 14 chiffres et clé de Luhn attendus.")
        return value


# Champs texte pouvant être écrits à la main : sert au service pour parcourir le corps.
MANUAL_TEXT_FIELDS: tuple[str, ...] = LEGAL_PROFILE_TEXT_FIELDS
