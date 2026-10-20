"""Schémas Pydantic : abonnements Web Push (phase 6c-iii-b).

Le navigateur fournit un endpoint et deux clés (`p256dh`, `auth`) qu'il a générées.
Aucun texte d'interface ici : le `kind` des messages poussés est une clé i18n et le
service worker traduit à l'affichage.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PushKeysIn(BaseModel):
    """Clés publiques du client (chiffrement du contenu, RFC 8291)."""

    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscribeIn(BaseModel):
    """Corps d'abonnement : ce que `PushSubscription.toJSON()` produit côté navigateur."""

    endpoint: str = Field(min_length=1, max_length=2048)
    keys: PushKeysIn
    user_agent: str | None = Field(default=None, max_length=255)


class PushUnsubscribeIn(BaseModel):
    """Corps de désabonnement : l'endpoint seul identifie l'abonnement."""

    endpoint: str = Field(min_length=1, max_length=2048)


class PushSubscriptionOut(BaseModel):
    """Abonnement enregistré (l'endpoint et l'utilisateur suffisent à l'identifier)."""

    id: uuid.UUID
    endpoint: str
    user_agent: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PushPublicKeyOut(BaseModel):
    """Clé VAPID publique à remettre au navigateur avant tout abonnement."""

    public_key: str
