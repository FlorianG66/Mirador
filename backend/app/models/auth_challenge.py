"""Table `auth_challenges` : défis d'authentification à usage unique (phase 2c).

Un défi est émis au premier facteur quand l'A2F est active, et remplacé par une
vraie session après vérification du second facteur. Seul son hachage SHA-256 est
stocké. Global d'identité comme `sessions` : pas de RLS (voir docs/DECISIONS.md).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuthChallenge(Base):
    """Preuve courte (5 minutes) que le premier facteur a réussi."""

    __tablename__ = "auth_challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Jeton opaque remis dans un cookie httpOnly : sa forme seule vit en base.
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
