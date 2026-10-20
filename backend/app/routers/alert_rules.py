"""Routes des règles d'alerte configurables (phase 6c-iii).

Quatre routes sous `/organizations/{organization_id}/alert-rules`. La lecture ne
montre que les modules visibles du membre (comme le Pouls et les objectifs) ; la
création, la modification et la suppression exigent `edit` sur le module de la
métrique — la vérification se fait dans le service, qui seul connaît la clé après
lecture du corps de la requête. Aucun try/except : les refus remontent en
`ServiceProblem`.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.permissions import get_current_tenant
from app.models.membership import Membership
from app.schemas.alert_rules import AlertRuleCreate, AlertRuleOut, AlertRuleUpdate
from app.services import alert_rules as alert_rules_service

router = APIRouter(prefix="/organizations/{organization_id}/alert-rules")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentTenant = Annotated[Membership, Depends(get_current_tenant)]


@router.get("", response_model=list[AlertRuleOut])
async def list_alert_rules(
    session: SessionDependency, membership: CurrentTenant
) -> list[AlertRuleOut]:
    """Règles des modules visibles (aucun refus possible)."""
    return await alert_rules_service.list_alert_rules(session, membership)


@router.post("", response_model=AlertRuleOut, status_code=201)
async def create_alert_rule(
    payload: AlertRuleCreate, session: SessionDependency, membership: CurrentTenant
) -> AlertRuleOut:
    """Crée une règle d'alerte (seuil franchi sur une métrique canonique)."""
    return await alert_rules_service.create_alert_rule(
        session, membership=membership, payload=payload
    )


@router.patch("/{rule_id}", response_model=AlertRuleOut)
async def update_alert_rule(
    rule_id: uuid.UUID,
    payload: AlertRuleUpdate,
    session: SessionDependency,
    membership: CurrentTenant,
) -> AlertRuleOut:
    """Modifie une règle existante (champs partiels)."""
    return await alert_rules_service.update_alert_rule(
        session, membership=membership, rule_id=rule_id, payload=payload
    )


@router.delete("/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: uuid.UUID, session: SessionDependency, membership: CurrentTenant
) -> Response:
    """Supprime une règle d'alerte."""
    await alert_rules_service.delete_alert_rule(session, membership=membership, rule_id=rule_id)
    return Response(status_code=204)
