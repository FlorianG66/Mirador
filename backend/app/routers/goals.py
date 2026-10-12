"""Routes des objectifs et budgets (phase 6) : cible sur n'importe quel KPI.

Quatre routes sous `/organizations/{organization_id}/goals`. La lecture ne
montre que les modules visibles du membre (comme le Pouls) ; la création, la
modification et la suppression exigent `edit` sur le module de la métrique — la
vérification se fait dans le service, qui seul connaît la clé après lecture du
corps de la requête. Aucun try/except : les refus remontent en `ServiceProblem`.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.permissions import get_current_tenant
from app.models.membership import Membership
from app.schemas.goals import GoalCreate, GoalOut, GoalUpdate
from app.services import goals as goals_service

router = APIRouter(prefix="/organizations/{organization_id}/goals")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentTenant = Annotated[Membership, Depends(get_current_tenant)]


@router.get("", response_model=list[GoalOut])
async def list_goals(session: SessionDependency, membership: CurrentTenant) -> list[GoalOut]:
    """Objectifs des modules visibles, avec leur progression calculée."""
    return await goals_service.list_goals(session, membership)


@router.post("", response_model=GoalOut, status_code=201)
async def create_goal(
    payload: GoalCreate, session: SessionDependency, membership: CurrentTenant
) -> GoalOut:
    """Crée un objectif (ou un budget) sur une métrique canonique."""
    return await goals_service.create_goal(session, membership=membership, payload=payload)


@router.patch("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: uuid.UUID,
    payload: GoalUpdate,
    session: SessionDependency,
    membership: CurrentTenant,
) -> GoalOut:
    """Modifie un objectif existant (champs partiels)."""
    return await goals_service.update_goal(
        session, membership=membership, goal_id=goal_id, payload=payload
    )


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: uuid.UUID, session: SessionDependency, membership: CurrentTenant
) -> Response:
    """Supprime un objectif."""
    await goals_service.delete_goal(session, membership=membership, goal_id=goal_id)
    return Response(status_code=204)
