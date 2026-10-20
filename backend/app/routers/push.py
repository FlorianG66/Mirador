"""Routes des abonnements Web Push (phase 6c-iii-b).

Trois routes sous `/organizations/{organization_id}/push` :

- `GET /public-key` : clé VAPID publique à donner au navigateur avant abonnement
  (404 tant que Web Push n'est pas configuré — le frontend masque alors le réglage).
- `POST /subscriptions` : enregistre (ou met à jour) l'abonnement du navigateur.
- `DELETE /subscriptions` : retire l'abonnement de l'appelant.

Tout est personnel à l'appelant : il n'y a pas de route pour lister les abonnements
d'autrui, et le service vérifie la propriété (`user_id`) avant toute suppression.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import get_request_settings, get_session
from app.core.permissions import get_current_tenant
from app.models.membership import Membership
from app.schemas.push import (
    PushPublicKeyOut,
    PushSubscribeIn,
    PushSubscriptionOut,
    PushUnsubscribeIn,
)
from app.services import push as push_service
from app.services.errors import ServiceProblem

router = APIRouter(prefix="/organizations/{organization_id}/push")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentTenant = Annotated[Membership, Depends(get_current_tenant)]
RequestSettings = Annotated[Settings, Depends(get_request_settings)]


@router.get("/public-key", response_model=PushPublicKeyOut)
async def get_public_key(settings: RequestSettings, membership: CurrentTenant) -> PushPublicKeyOut:
    """Clé VAPID publique ; 404 si Web Push n'est pas configuré sur ce serveur."""
    key = push_service.public_key(settings)
    if key is None:
        raise ServiceProblem(404, "Web Push non configuré.")
    return PushPublicKeyOut(public_key=key)


@router.post("/subscriptions", response_model=PushSubscriptionOut, status_code=201)
async def subscribe(
    payload: PushSubscribeIn, session: SessionDependency, membership: CurrentTenant
) -> PushSubscriptionOut:
    """Enregistre l'abonnement d'un navigateur pour l'appelant (idempotent)."""
    return await push_service.subscribe(session, membership=membership, payload=payload)


@router.delete("/subscriptions", status_code=204)
async def unsubscribe(
    payload: PushUnsubscribeIn, session: SessionDependency, membership: CurrentTenant
) -> Response:
    """Retire l'abonnement d'un endpoint pour l'appelant (idempotent)."""
    await push_service.unsubscribe(session, membership=membership, endpoint=payload.endpoint)
    return Response(status_code=204)
