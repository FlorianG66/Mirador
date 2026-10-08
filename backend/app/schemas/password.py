"""Schémas Pydantic des routes de récupération de mot de passe (phase 2c)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.auth import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Toujours identique, que le compte existe ou non (anti-énumération)."""

    status: Literal["ok"] = "ok"


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
