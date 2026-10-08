"""Table `sessions` : jetons d'accès et de rafraîchissement, globale comme `users`.

Pas de RLS ici (voir docs/DECISIONS.md) : une session appartient à un compte,
pas à une organisation ; l'isolation se joue sur les memberships.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserSession(Base):
    """Une session navigateur : deux jetons opaques hachés, un jeton CSRF lisible."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    access_token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    refresh_token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Renvoyé au navigateur dans un cookie lisible par le JS (double submit CSRF).
    csrf_token: Mapped[str] = mapped_column(Text, nullable=False)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
