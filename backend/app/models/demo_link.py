"""Table `demo_links` : liens `/demo/<token>` à durée limitée (SPEC §9).

Un lien est une *capacité* : il ouvre une organisation de démonstration sans
compte. Comme `sessions` et les invitations, seul le hachage du jeton est stocké ;
la table reste hors RLS car un lien n'appartient à aucun tenant. L'organisation et
le créateur sont conservés pour l'audit, mais leur suppression ne casse rien.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DemoLink(Base):
    """Un lien de démonstration : secteur, jeton haché et échéance."""

    __tablename__ = "demo_links"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    sector: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Traçabilité : l'admin qui a créé le lien et son organisation d'origine.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
