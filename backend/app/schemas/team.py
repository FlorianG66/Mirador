"""Schémas Pydantic des routes d'équipe : membres, permissions, audit (phase 2d)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr

from app.models.enums import Module, PermissionLevel, Role


class MemberOut(BaseModel):
    """Un membre de l'organisation avec ses niveaux effectifs."""

    user_id: uuid.UUID
    email: EmailStr
    role: Role
    modules: dict[Module, PermissionLevel]


class MyPermissionsOut(BaseModel):
    """Niveaux du membre courant : sert aux gardes de routes côté frontend."""

    role: Role
    modules: dict[Module, PermissionLevel]


class UpdatePermissionsRequest(BaseModel):
    """Remplacement complet des niveaux : un module omis retombe à `none`."""

    modules: dict[Module, PermissionLevel]


class PermissionsOut(BaseModel):
    """Niveaux effectifs après mise à jour."""

    modules: dict[Module, PermissionLevel]


class AuditLogOut(BaseModel):
    """Entrée du journal des actions sensibles (verbatim, l'UI traduit)."""

    id: uuid.UUID
    action: str
    actor_user_id: uuid.UUID | None
    resource_type: str | None
    resource_id: str | None
    payload: dict[str, Any] | None
    created_at: datetime
