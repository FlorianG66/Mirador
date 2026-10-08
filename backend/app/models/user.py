"""Table `users` : comptes utilisateurs, identité globale hors RLS (voir DECISIONS)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Un compte. Peut appartenir à plusieurs organisations (le MVP n'en crée qu'une)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    # Normalisé en minuscules par l'application ; la contrainte le garantit aussi en base.
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Null pour un compte créé via Google OIDC (aucun mot de passe local).
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A2F TOTP (SPEC §2) : secret nullable, activation datée (phase 2c).
    # Le secret est stocké en clair au repos : voir docs/DECISIONS.md (chiffrement
    # AES-GCM prévu avec le module des connexions tierces, SPEC §6).
    totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (CheckConstraint("email = lower(email)", name="users_email_lowercase"),)
