"""Route du Pouls (phase 5f) : agrégat de la page d'accueil.

Pas de garde de module : la route restreint elle-même chaque KPI aux modules
visibles du membre. Un membre sans aucun module reçoit un Pouls vide (santé
`unknown`), jamais une erreur d'autorisation.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.permissions import get_current_tenant
from app.models.membership import Membership
from app.schemas.pulse import PulseOut
from app.services import pulse as pulse_service

router = APIRouter(prefix="/organizations/{organization_id}")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentTenant = Annotated[Membership, Depends(get_current_tenant)]


@router.get("/pulse", response_model=PulseOut)
async def read_pulse(
    session: SessionDependency,
    membership: CurrentTenant,
) -> PulseOut:
    """Pouls de l'organisation active : KPI clés, santé et fil d'activité.

    Le fil d'activité (journal d'audit) n'est renvoyé qu'aux administrateurs ;
    pour un membre, la route l'omet sans erreur.
    """
    return await pulse_service.build_pulse(session, membership=membership)
