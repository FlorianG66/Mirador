"""Routes de la fiche légale (phase 5e) : lecture, saisie manuelle, rafraîchissement.

Trois routes sous `/organizations/{organization_id}/legal`, gardées par le module
`legal` : `view` pour lire, `edit` pour saisir ou rafraîchir (l'admin a `edit` par
défaut, SPEC §2). Aucun try/except : les refus remontent en `ServiceProblem` géré
au centre (`app.core.errors`).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_legal_registry, get_session
from app.core.permissions import require_module
from app.models.enums import Module, PermissionLevel, Role
from app.models.membership import Membership
from app.repositories import organizations as organizations_repository
from app.schemas.legal import LegalProfileOut, LegalProfileUpdate
from app.services import legal as legal_service
from app.services.legal_registry import LegalRegistry

router = APIRouter(prefix="/organizations/{organization_id}/legal")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CanView = Annotated[Membership, Depends(require_module(Module.LEGAL, PermissionLevel.VIEW))]
CanEdit = Annotated[Membership, Depends(require_module(Module.LEGAL, PermissionLevel.EDIT))]
RegistryDependency = Annotated[LegalRegistry, Depends(get_legal_registry)]


async def _organization_siren(session: AsyncSession, membership: Membership) -> str | None:
    """SIREN de l'organisation (renseigné à l'inscription), source de repli pour la fiche."""
    organization = await organizations_repository.get_organization(
        session, membership.organization_id
    )
    return organization.siren if organization is not None else None


@router.get("", response_model=LegalProfileOut)
async def read_legal_profile(session: SessionDependency, membership: CanView) -> LegalProfileOut:
    """Fiche légale de l'organisation ; dirigeants masqués pour un membre non-admin."""
    return await legal_service.get_profile(
        session,
        organization_id=membership.organization_id,
        organization_siren=await _organization_siren(session, membership),
        include_directors=membership.role == Role.ADMIN.value,
    )


@router.put("", response_model=LegalProfileOut)
async def update_legal_profile(
    payload: LegalProfileUpdate, session: SessionDependency, membership: CanEdit
) -> LegalProfileOut:
    """Écrit la saisie manuelle (source `manual`) : ces valeurs priment sur le registre."""
    return await legal_service.update_profile(
        session,
        organization_id=membership.organization_id,
        organization_siren=await _organization_siren(session, membership),
        actor_user_id=membership.user_id,
        payload=payload,
    )


@router.post("/refresh", response_model=LegalProfileOut)
async def refresh_legal_profile(
    session: SessionDependency, membership: CanEdit, registry: RegistryDependency
) -> LegalProfileOut:
    """Recharge la fiche depuis le registre, sans écraser la saisie manuelle."""
    return await legal_service.refresh_profile(
        session,
        organization_id=membership.organization_id,
        organization_siren=await _organization_siren(session, membership),
        actor_user_id=membership.user_id,
        registry=registry,
    )
