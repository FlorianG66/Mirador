"""Schémas Pydantic des routes d'invitation (phase 2d)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Module, PermissionLevel, Role


class InvitationCreateRequest(BaseModel):
    """Émission : modules visibles choisis pour le futur membre (SPEC §2)."""

    email: EmailStr
    role: Role = Role.MEMBER
    modules: dict[Module, PermissionLevel] = Field(default_factory=dict)


class InvitationOut(BaseModel):
    """Invitation telle que l'admin la voit (niveaux effectifs annoncés)."""

    id: uuid.UUID
    email: EmailStr
    role: Role
    modules: dict[Module, PermissionLevel]
    expires_at: datetime


class AcceptInvitationRequest(BaseModel):
    """Acceptation : le lien d'e-mail contient le jeton et l'organisation."""

    token: str = Field(min_length=1, max_length=512)
    organization_id: uuid.UUID


class AcceptInvitationResponse(BaseModel):
    """Rattachement créé et niveaux effectivement obtenus."""

    organization_id: uuid.UUID
    role: Role
    modules: dict[Module, PermissionLevel]
