"""Routes des notifications in-app (phase 6c-ii).

Chaque utilisateur ne voit et ne manipule que ses propres notifications.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.permissions import get_current_tenant
from app.models.membership import Membership
from app.repositories import notifications as notifications_repository
from app.schemas.notifications import NotificationListOut, NotificationOut
from app.services.errors import ServiceProblem

router = APIRouter(prefix="/organizations/{organization_id}/notifications")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentTenant = Annotated[Membership, Depends(get_current_tenant)]


@router.get("", response_model=NotificationListOut)
async def list_notifications(
    session: SessionDependency, membership: CurrentTenant
) -> NotificationListOut:
    """Notifications personnelles de l'appelant, de la plus récente à la plus ancienne."""
    items = await notifications_repository.list_notifications(
        session, organization_id=membership.organization_id, user_id=membership.user_id
    )
    unread = await notifications_repository.get_unread_count(
        session, organization_id=membership.organization_id, user_id=membership.user_id
    )
    return NotificationListOut(
        items=[NotificationOut.model_validate(item) for item in items], unread_count=unread
    )


@router.post("/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: uuid.UUID,
    session: SessionDependency,
    membership: CurrentTenant,
) -> Response:
    """Marque une notification de l'appelant comme lue (404 si elle appartient à un autre)."""
    notification = await notifications_repository.get_for_user(
        session,
        notification_id=notification_id,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
    )
    if notification is None:
        raise ServiceProblem(404, "Notification introuvable.")
    await notifications_repository.mark_read(session, notification)
    return Response(status_code=204)


@router.post("/read-all", status_code=204)
async def mark_all_read(session: SessionDependency, membership: CurrentTenant) -> Response:
    """Marque comme lues toutes les notifications non lues de l'appelant."""
    await notifications_repository.mark_all_read(
        session, organization_id=membership.organization_id, user_id=membership.user_id
    )
    return Response(status_code=204)
