"""Table `module_permissions` : niveau d'accès d'un membre sur un module (SPEC §2)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import LEVEL_VALUES_SQL, MODULE_VALUES_SQL


class ModulePermission(Base):
    """`none` / `view` / `edit` sur un module, pour un membership donné."""

    __tablename__ = "module_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    # Redondant avec le membership : nécessaire au filtre de tenant (RLS) sans jointure.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False
    )
    module: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("membership_id", "module", name="module_permissions_membership_module"),
        CheckConstraint(f"module IN ({MODULE_VALUES_SQL})", name="module_permissions_module_known"),
        CheckConstraint(f"level IN ({LEVEL_VALUES_SQL})", name="module_permissions_level_known"),
    )
