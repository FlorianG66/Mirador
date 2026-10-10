"""Dépendances d'autorisation : tenant de l'organisation, rôle admin, accès module.

C'est aussi la couche « permissions » : la règle d'affichage des niveaux (l'admin a
`edit` partout) et les conversions entre la forme API (dictionnaire) et la forme
stockée en JSONB (liste de paires module/niveau, cf. modèle `invitations`).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Iterable
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session
from app.core.tenancy import set_tenant
from app.models.enums import Module, PermissionLevel, Role
from app.models.membership import Membership
from app.models.user import User
from app.repositories import memberships as memberships_repository
from app.repositories import module_permissions as module_permissions_repository

# Ordre d'accès none < view < edit : pour comparer un niveau requis au niveau donné.
_LEVEL_RANK = {
    PermissionLevel.NONE: 0,
    PermissionLevel.VIEW: 1,
    PermissionLevel.EDIT: 2,
}


async def get_current_tenant(
    organization_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> Membership:
    """Rattachement de l'utilisateur à l'organisation de la route ; 403 sinon.

    Pose l'organisation active : c'est elle qui alimente la RLS de toutes les
    requêtes de la transaction (défense en profondeur, cf. migration 0002).
    """
    membership = await memberships_repository.get_membership(
        session, organization_id=organization_id, user_id=user.id
    )
    if membership is None:
        raise HTTPException(403, "Vous n'avez pas accès à cette organisation.")
    await set_tenant(session, user_id=user.id, organization_id=organization_id)
    return membership


async def require_admin(
    membership: Annotated[Membership, Depends(get_current_tenant)],
) -> Membership:
    """Action réservée au rôle `admin` : invitations, permissions, révocation (SPEC §2)."""
    if membership.role != Role.ADMIN.value:
        raise HTTPException(403, "Réservé aux administrateurs.")
    return membership


def require_module(module: Module, level: PermissionLevel) -> Callable[..., Awaitable[Membership]]:
    """Garde d'accès à un module : niveau requis `view` ou `edit` (SPEC §2).

    L'admin a tous les droits sans ligne en base ; un module sans ligne vaut `none`.
    La dépendance suppose le tenant posé : elle est posée par `get_current_tenant`.
    """

    async def dependency(
        session: Annotated[AsyncSession, Depends(get_session)],
        membership: Annotated[Membership, Depends(get_current_tenant)],
    ) -> Membership:
        return await ensure_module_access(session, membership, module, level)

    return dependency


async def ensure_module_access(
    session: AsyncSession,
    membership: Membership,
    module: Module,
    level: PermissionLevel,
) -> Membership:
    """Vérifie le niveau d'accès d'un membre sur un module (admin : tous les droits)."""
    if membership.role == Role.ADMIN.value:
        return membership
    granted = await module_permissions_repository.get_level(
        session, membership_id=membership.id, module=module
    )
    current = PermissionLevel(granted) if granted is not None else PermissionLevel.NONE
    if _LEVEL_RANK[current] < _LEVEL_RANK[level]:
        raise HTTPException(403, f"Accès « {level} » requis pour le module « {module} ».")
    return membership


def modules_for(role: str, choices: dict[Module, PermissionLevel]) -> dict[Module, PermissionLevel]:
    """Niveaux effectifs des cinq modules : `edit` partout pour un admin (SPEC §2).

    Un module absent des choix vaut `none` : la réponse couvre toujours les cinq.
    """
    if role == Role.ADMIN.value:
        return {module: PermissionLevel.EDIT for module in Module}
    return {module: choices.get(module, PermissionLevel.NONE) for module in Module}


def modules_to_rows(modules: dict[Module, PermissionLevel]) -> list[dict[str, str]]:
    """Forme stockée en JSONB : seuls les niveaux différents de `none` (défaut)."""
    return [
        {"module": module.value, "level": level.value}
        for module, level in modules.items()
        if level != PermissionLevel.NONE
    ]


def modules_from_rows(rows: Iterable[dict[str, Any]]) -> dict[Module, PermissionLevel]:
    """Reconstruit le dictionnaire de choix depuis le JSONB stocké en base."""
    return {Module(row["module"]): PermissionLevel(row["level"]) for row in rows}


def modules_to_plain(modules: dict[Module, PermissionLevel]) -> dict[str, str]:
    """Forme JSON du journal d'audit : dictionnaire de chaînes lisibles."""
    return {module.value: level.value for module, level in modules.items()}
