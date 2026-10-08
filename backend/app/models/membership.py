"""Table `memberships` : rattachement d'un utilisateur à une organisation, avec son rôle."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ROLE_VALUES_SQL


class Membership(Base):
    """Un utilisateur dans une organisation : `admin` (dirigeant) ou `member` (SPEC §2)."""

    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="memberships_organization_user"),
        CheckConstraint(f"role IN ({ROLE_VALUES_SQL})", name="memberships_role_known"),
    )
