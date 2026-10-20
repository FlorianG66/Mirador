"""Service Web Push (SPEC §4, phase 6c-iii-b).

Deux responsabilités, séparées volontairement :

1. **Gestion des abonnements** : un navigateur s'abonne (`subscribe`) ou se
   désabonne (`unsubscribe`) ; l'endpoint rend l'opération idempotente.
2. **Envoi** : à chaque notification émise pour un utilisateur, on pousse un
   message vers chacun de ses abonnements. L'envoi passe par une interface
   `PushSender` : `WebPushSender` parle le vrai protocole (VAPID + chiffrement),
   un faux la remplace en test — aucun service de push ni clé réelle n'étant
   requis en test ou en CI (AGENTS.md §5).

L'envoi est **best-effort** : une erreur de push ne fait jamais échouer l'émission
de la notification in-app (qui reste la source de vérité). Un abonnement déclaré
absent par le service de push (`gone`) est supprimé : il ne pourra plus recevoir.
"""

from __future__ import annotations

import json
import logging
import uuid
from enum import StrEnum
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.membership import Membership
from app.models.push_subscription import PushSubscription
from app.repositories import push_subscriptions as push_subscriptions_repository
from app.schemas.push import PushSubscribeIn, PushSubscriptionOut
from app.services import audit as audit_service

logger = logging.getLogger(__name__)

#: Codes HTTP par lesquels un service de push signale un abonnement caduc.
GONE_STATUS_CODES = frozenset({404, 410})


class PushOutcome(StrEnum):
    """Résultat d'un envoi vers un abonnement donné."""

    DELIVERED = "delivered"
    #: L'abonnement n'existe plus côté service de push : à supprimer.
    GONE = "gone"
    #: Panne transitoire (réseau, service indisponible) : on garde l'abonnement.
    FAILED = "failed"


class PushMessage(Protocol):
    """Contenu d'un message push : des données neutres, jamais un texte figé.

    Le texte affiché est reconstruit par le service worker à partir du `kind`
    (clé i18n) et des `params`, exactement comme la notification in-app.
    """

    @property
    def kind(self) -> str: ...

    @property
    def params(self) -> dict[str, object]: ...

    @property
    def link(self) -> str | None: ...


class PushSender(Protocol):
    """Interface d'envoi d'un message vers un abonnement (injectable en test)."""

    async def send(
        self, subscription: PushSubscription, message: dict[str, object]
    ) -> PushOutcome: ...


class WebPushSender:
    """Envoi réel via VAPID, au nom du serveur (clés lues dans la configuration)."""

    def __init__(self, settings: Settings) -> None:
        self._private_key = settings.vapid_private_key
        # `sub` est une URL de contact exigée par les services de push (RFC 8292) :
        # on réutilise la base publique de l'application comme identifiant.
        self._subject = settings.vapid_subject or settings.app_base_url

    async def send(self, subscription: PushSubscription, message: dict[str, object]) -> PushOutcome:
        """Pousse un message chiffré ; traduit l'échec en `PushOutcome`."""
        if not self._private_key:
            logger.warning("Web Push désactivé : aucune clé VAPID privée configurée.")
            return PushOutcome.FAILED
        # Import local : la bibliothèque n'est requise que lorsque l'envoi réel
        # est réellement tenté (les tests utilisent un faux émetteur).
        from pywebpush import WebPushException, webpush_async

        try:
            await webpush_async(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps(message),
                vapid_private_key=self._private_key,
                vapid_claims={"sub": self._subject},
                timeout=10,
            )
        except WebPushException as error:
            status_code = error.status_code
            if status_code in GONE_STATUS_CODES:
                return PushOutcome.GONE
            logger.warning("Envoi Web Push en échec (statut %s).", status_code)
            return PushOutcome.FAILED
        except Exception:
            # Panne réseau ou réponse illisible : jamais d'échec remonté à l'appelant.
            logger.exception("Envoi Web Push en échec.")
            return PushOutcome.FAILED
        return PushOutcome.DELIVERED


def public_key(settings: Settings) -> str | None:
    """Clé VAPID publique à remettre au navigateur, ou `None` si non configurée."""
    return settings.vapid_public_key or None


async def subscribe(
    session: AsyncSession, *, membership: Membership, payload: PushSubscribeIn
) -> PushSubscriptionOut:
    """Enregistre (ou met à jour) l'abonnement d'un navigateur pour l'appelant.

    Idempotent : le même endpoint met à jour les clés au lieu de créer un doublon
    (un navigateur qui se réabonne après avoir tourné ses clés reste suivi).
    """
    existing = await push_subscriptions_repository.get_by_endpoint(session, payload.endpoint)
    if existing is not None and existing.user_id == membership.user_id:
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        existing.user_agent = payload.user_agent
        await session.flush()
        return PushSubscriptionOut.model_validate(existing)
    if existing is not None:
        # L'endpoint appartient à un autre utilisateur (rare : navigateur partagé) :
        # on le réattribue à l'appelant, qui vient de s'y abonner.
        existing.user_id = membership.user_id
        existing.organization_id = membership.organization_id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        existing.user_agent = payload.user_agent
        await session.flush()
        return PushSubscriptionOut.model_validate(existing)
    subscription = await push_subscriptions_repository.create(
        session,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth=payload.keys.auth,
        user_agent=payload.user_agent,
    )
    await session.flush()
    await audit_service.record(
        session,
        organization_id=membership.organization_id,
        actor_user_id=membership.user_id,
        action="push.subscribed",
        resource_type="push_subscription",
        resource_id=str(subscription.id),
        payload={},
    )
    return PushSubscriptionOut.model_validate(subscription)


async def unsubscribe(session: AsyncSession, *, membership: Membership, endpoint: str) -> None:
    """Retire l'abonnement d'un endpoint pour l'appelant (idempotent)."""
    removed = await push_subscriptions_repository.delete_by_endpoint(
        session,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        endpoint=endpoint,
    )
    if removed:
        await audit_service.record(
            session,
            organization_id=membership.organization_id,
            actor_user_id=membership.user_id,
            action="push.unsubscribed",
            resource_type="push_subscription",
            resource_id=endpoint,
            payload={},
        )


async def send_to_user(
    session: AsyncSession,
    *,
    sender: PushSender | None,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    message: dict[str, object],
) -> None:
    """Pousse `message` vers tous les abonnements de l'utilisateur (best-effort).

    Sans émetteur configuré (Web Push désactivé), l'appel est un succès sans effet :
    la notification in-app reste, elle, toujours créée. Un abonnement que le service
    de push déclare caduc est supprimé au passage.
    """
    if sender is None:
        return
    subscriptions = await push_subscriptions_repository.list_for_user(
        session, organization_id=organization_id, user_id=user_id
    )
    for subscription in subscriptions:
        outcome = await sender.send(subscription, message)
        if outcome == PushOutcome.GONE:
            await push_subscriptions_repository.delete_by_id(session, subscription)


def message_for(kind: str, params: dict[str, object], link: str | None) -> dict[str, object]:
    """Assemble le corps d'un push : strictement la même information que la notification."""
    return {"kind": kind, "params": params, "link": link}
