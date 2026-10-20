"""Schémas Pydantic : notifications (phase 6c-ii)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationOut(BaseModel):
    """Détail d'une notification in-app."""

    id: uuid.UUID
    kind: str
    params: dict[str, Any]
    link: str | None
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListOut(BaseModel):
    """Liste paginée des notifications + compteur de non-lus."""

    items: list[NotificationOut]
    unread_count: int = Field(ge=0)
