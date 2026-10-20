"""Table `push_subscriptions` : abonnements Web Push (SPEC §4, phase 6c-iii-b).

Un abonnement est créé par un navigateur pour un utilisateur donné (endpoint unique
fourni par le service de push, plus les clés de chiffrement `p256dh`/`auth`). Comme
les autres tables tenant, il porte `organization_id` et vit sous RLS : un utilisateur
d'une organisation ne voit jamais les abonnements d'une autre. Les abonnements sont
personnels à `user_id` mais rattachés à l'organisation active au moment de
l'abonnement — la notification portée par un push est toujours contextuelle.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PushSubscription(Base):
    """Abonnement Web Push d'un navigateur pour un utilisateur d'une organisation."""

    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: URL d'envoi fournie par le navigateur (`PushSubscription.endpoint`).
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    #: Clé publique du client (chiffrement du message, courbe P-256).
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    #: Secret d'authentification du client (dérivation de la clé partagée).
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    #: Agent utilisateur au moment de l'abonnement (diagnostic uniquement).
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        # Un endpoint identifie un abonnement de navigateur : le renouveler met à
        # jour la ligne existante plutôt que d'en empiler une deuxième.
        UniqueConstraint("endpoint", name="push_subscriptions_endpoint_unique"),
        Index("ix_push_subscriptions_org_user", "organization_id", "user_id"),
    )
