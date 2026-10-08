"""Table `backup_codes` : codes de secours de l'A2F (phase 2c).

Seul le hachage SHA-256 de chaque code est stocké, comme les jetons de session :
un code est haute entropie (40 bits) et le poste de vérification est quota limité,
le sel n'apporterait rien ici (voir docs/DECISIONS.md). Un code consommé est marqué
`used_at` et ne peut pas être rejoué. Global d'identité : pas de RLS.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BackupCode(Base):
    """Un code de secours émis lors de l'activation de l'A2F."""

    __tablename__ = "backup_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
