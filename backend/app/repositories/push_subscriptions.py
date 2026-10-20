"""Repository : `push_subscriptions` (accès aux données uniquement, aucune règle métier).

Toutes les requêtes sont filtrées par organisation (RLS en défense en profondeur
+ filtres explicites). L'endpoint est la clé naturelle d'un abonnement : le
réabonnement d'un même navigateur met à jour la ligne existante.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_subscription import PushSubscription


async def list_for_user(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> list[PushSubscription]:
    """Abonnements d'un utilisateur dans une organisation (ordre stable)."""
    result = await session.execute(
        select(PushSubscription)
        .where(
            PushSubscription.organization_id == organization_id,
            PushSubscription.user_id == user_id,
        )
        .order_by(PushSubscription.created_at, PushSubscription.id)
    )
    return list(result.scalars().all())


async def get_by_endpoint(session: AsyncSession, endpoint: str) -> PushSubscription | None:
    """Abonnement par endpoint (unique), quelle que soit l'organisation (RLS s'applique)."""
    result = await session.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    return result.scalar_one_or_none()


async def create(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None,
) -> PushSubscription:
    """Instancie un abonnement (non flushé) : le service l'audite puis le committe."""
    subscription = PushSubscription(
        organization_id=organization_id,
        user_id=user_id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=user_agent,
    )
    session.add(subscription)
    return subscription


async def delete_by_endpoint(
    session: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, endpoint: str
) -> int:
    """Supprime l'abonnement d'un endpoint pour cet utilisateur ; renvoie le nombre retiré.

    Le filtre `user_id` empêche un utilisateur de désabonner l'appareil d'un autre :
    l'endpoint suffit techniquement, mais la propriété est vérifiée explicitement.
    """
    result = await session.execute(
        delete(PushSubscription).where(
            PushSubscription.organization_id == organization_id,
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
    )
    await session.flush()
    # Un DELETE sans RETURNING renvoie un CursorResult : `rowcount` y est défini.
    return int(getattr(result, "rowcount", 0) or 0)


async def delete_by_id(session: AsyncSession, subscription: PushSubscription) -> None:
    """Supprime un abonnement précis (utilisé quand le service de push le déclare absent)."""
    await session.delete(subscription)
