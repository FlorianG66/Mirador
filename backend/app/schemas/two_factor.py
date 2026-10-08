"""Schémas Pydantic des routes A2F (phase 2c)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.auth import PASSWORD_MAX_LENGTH


class EnableTwoFactorRequest(BaseModel):
    """Active (ou réactive) le TOTP : le mot de passe courant est exigé."""

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class DisableTwoFactorRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class TwoFactorVerifyRequest(BaseModel):
    """Code TOTP à 6 chiffres, ou code de secours de 8 caractères."""

    code: str = Field(min_length=6, max_length=12)


class TOTPSetupResponse(BaseModel):
    """Ce que le frontend affiche une seule fois : secret, QR code, codes de secours."""

    secret: str
    otpauth_url: str
    backup_codes: list[str]
