"""Schémas Pydantic des routes d'authentification (entrée/sortie)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.siren import is_valid_siren
from app.models.enums import Role

# ASVS L2 : longueur minimale raisonnable pour un mot de passe utilisateur.
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


class RegisterRequest(BaseModel):
    """Inscription : crée le compte, l'organisation et le rattachement admin."""

    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    organization_name: str = Field(min_length=1, max_length=100)
    siren: str | None = Field(default=None, pattern=r"^[0-9]{9}$")

    @field_validator("siren")
    @classmethod
    def _siren_passes_luhn(cls, value: str | None) -> str | None:
        """Champ optionnel, mais s'il est présent il doit être valide (clé de Luhn)."""
        if value is not None and not is_valid_siren(value):
            raise ValueError("SIREN invalide (clé de Luhn échouée)")
        return value


class LoginRequest(BaseModel):
    """Connexion e-mail/mot de passe."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserOut(BaseModel):
    """Identité publique d'un compte."""

    id: uuid.UUID
    email: EmailStr


class OrganizationOut(BaseModel):
    """Identité publique d'une organisation."""

    id: uuid.UUID
    name: str


class RegisterResponse(BaseModel):
    user: UserOut
    organization: OrganizationOut


class LoginResponse(BaseModel):
    """Connexion : session distribuée, ou défi A2F à présenter d'abord."""

    user: UserOut | None = None
    totp_required: bool = False


class MembershipOut(BaseModel):
    """Rattachement de l'utilisateur courant à une organisation."""

    organization_id: uuid.UUID
    role: Role


class MeResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    memberships: list[MembershipOut]
