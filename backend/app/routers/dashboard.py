"""Routes du tableau de bord personnalisable (phase 6b-ii).

Trois routes sous `/organizations/{organization_id}/dashboard`. La mise en page
est personnelle : chaque membre lit et enregistre la sienne, aucun droit de module
n'est exigé (ce n'est pas une donnée métier mais une préférence de disposition).
Le catalogue renvoyé est, lui, filtré par les droits du membre. Aucun try/except :
les refus remontent en `ServiceProblem`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.permissions import get_current_tenant
from app.models.membership import Membership
from app.schemas.dashboard import DashboardLayoutUpdate, DashboardOut
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/organizations/{organization_id}/dashboard")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentTenant = Annotated[Membership, Depends(get_current_tenant)]


@router.get("", response_model=DashboardOut)
async def read_dashboard(session: SessionDependency, membership: CurrentTenant) -> DashboardOut:
    """Mise en page du membre (ou disposition par défaut) et catalogue autorisé."""
    return await dashboard_service.get_layout(session, membership)


@router.put("", response_model=DashboardOut)
async def save_dashboard(
    payload: DashboardLayoutUpdate, session: SessionDependency, membership: CurrentTenant
) -> DashboardOut:
    """Enregistre la mise en page du membre (remplace la précédente)."""
    return await dashboard_service.save_layout(session, membership=membership, payload=payload)


@router.delete("", status_code=204)
async def reset_dashboard(session: SessionDependency, membership: CurrentTenant) -> Response:
    """Remet la mise en page du membre à la disposition par défaut."""
    await dashboard_service.reset_layout(session, membership=membership)
    return Response(status_code=204)
