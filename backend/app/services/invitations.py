"""Service d'invitation : émission, liste, révocation, acceptation (SPEC §2).

Le jeton d'acceptation est aléatoire et stocké haché. L'e-mail contient le jeton
**et** l'organisation : la RLS n'autorise qu'une organisation à lire ses propres
invitations, et l'invité n'est pas encore membre — le lien porte donc le tenant.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import INVITATION_TTL_SECONDS, PROJECT_NAME
from app.core.permissions import (
    modules_for,
    modules_from_rows,
    modules_to_plain,
    modules_to_rows,
)
from app.core.security import generate_token, hash_token
from app.core.tenancy import set_tenant
from app.models.enums import Module, PermissionLevel, Role
from app.models.invitation import Invitation
from app.models.user import User
from app.repositories import invitations as invitations_repository
from app.repositories import memberships as memberships_repository
from app.repositories import module_permissions as module_permissions_repository
from app.repositories import users as users_repository
from app.schemas.invitations import AcceptInvitationResponse, InvitationOut
from app.services import audit as audit_service
from app.services.emails import EmailSender
from app.services.errors import ServiceProblem


def _accept_link(base_url: str, token: str, organization_id: uuid.UUID) -> str:
    return f"{base_url}/invitations/accept?token={token}&organization={organization_id}"


def _to_out(invitation: Invitation, modules: dict[Module, PermissionLevel]) -> InvitationOut:
    return InvitationOut(
        id=invitation.id,
        email=invitation.email,
        role=Role(invitation.role),
        modules=modules,
        expires_at=invitation.expires_at,
    )


async def invite(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor: User,
    email: str,
    role: Role,
    modules: dict[Module, PermissionLevel],
    base_url: str,
    sender: EmailSender,
) -> InvitationOut:
    """Émet l'invitation et demande l'envoi de l'e-mail (409 si déjà fait)."""
    existing_user = await users_repository.get_user_by_email(session, email)
    if existing_user is not None:
        membership = await memberships_repository.get_membership(
            session, organization_id=organization_id, user_id=existing_user.id
        )
        if membership is not None:
            raise ServiceProblem(409, "Cet e-mail est déjà membre de l'organisation.")
    pending = await invitations_repository.get_pending_by_email(
        session, organization_id=organization_id, email=email
    )
    if pending is not None:
        raise ServiceProblem(409, "Une invitation est déjà en attente pour cet e-mail.")

    token = generate_token()
    invitation = await invitations_repository.create_invitation(
        session,
        organization_id=organization_id,
        invited_by_id=actor.id,
        email=email,
        role=role.value,
        module_permissions=modules_to_rows(modules),
        token_hash=hash_token(token),
        expires_at=datetime.now(UTC) + timedelta(seconds=INVITATION_TTL_SECONDS),
    )
    await audit_service.record(
        session,
        organization_id=organization_id,
        actor_user_id=actor.id,
        action="invitation.created",
        resource_type="invitation",
        resource_id=str(invitation.id),
        payload={"email": email, "role": role.value, "modules": modules_to_plain(modules)},
    )
    await sender.send(
        to=email,
        subject=f"Invitation à rejoindre {PROJECT_NAME}",
        content=(
            "Bonjour,\n\n"
            f"Vous êtes invité(e) à rejoindre une organisation sur {PROJECT_NAME} "
            f"avec le compte {email}.\n"
            f"Ce lien est valable {INVITATION_TTL_SECONDS // (24 * 3600)} jours :\n\n"
            f"{_accept_link(base_url, token, organization_id)}\n\n"
            "Connectez-vous avec cet e-mail puis ouvrez le lien pour accepter. "
            "Si vous n'êtes pas concerné(e), ignorez cet e-mail.\n"
        ),
    )
    return _to_out(invitation, modules_for(role.value, modules))


async def list_pending(session: AsyncSession, *, organization_id: uuid.UUID) -> list[InvitationOut]:
    """Invitations en attente et non expirées de l'organisation."""
    invitations = await invitations_repository.list_pending(
        session, organization_id=organization_id
    )
    return [
        _to_out(
            invitation,
            modules_for(invitation.role, modules_from_rows(invitation.module_permissions)),
        )
        for invitation in invitations
    ]


async def revoke(
    session: AsyncSession, *, organization_id: uuid.UUID, invitation_id: uuid.UUID
) -> None:
    """Annule une invitation : son jeton ne vaut plus rien (404 si inconnue)."""
    invitation = await invitations_repository.get_by_id(
        session, organization_id=organization_id, invitation_id=invitation_id
    )
    if invitation is None or invitation.accepted_at is not None:
        raise ServiceProblem(404, "Invitation introuvable.")
    await audit_service.record(
        session,
        organization_id=organization_id,
        actor_user_id=invitation.invited_by_id,
        action="invitation.revoked",
        resource_type="invitation",
        resource_id=str(invitation.id),
        payload={"email": invitation.email},
    )
    await invitations_repository.delete(session, invitation)


async def accept(
    session: AsyncSession, *, user: User, token: str, organization_id: uuid.UUID
) -> AcceptInvitationResponse:
    """Consomme l'invitation : rattachement + permissions choisies, une seule fois.

    L'organisation du lien est posée avant la lecture : c'est la condition RLS pour
    voir l'invitation, l'invité n'ayant encore aucun rattachement.
    """
    await set_tenant(session, user_id=user.id, organization_id=organization_id)
    invitation = await invitations_repository.get_by_token_hash(
        session, token_hash=hash_token(token), organization_id=organization_id
    )
    now = datetime.now(UTC)
    if invitation is None or invitation.accepted_at is not None or invitation.expires_at <= now:
        raise ServiceProblem(401, "Invitation invalide ou expirée.")
    if invitation.email.lower() != user.email.lower():
        raise ServiceProblem(403, "Cette invitation n'est pas destinée à cet e-mail.")
    existing = await memberships_repository.get_membership(
        session, organization_id=organization_id, user_id=user.id
    )
    if existing is not None:
        raise ServiceProblem(409, "Vous êtes déjà membre de cette organisation.")

    role = Role(invitation.role)
    membership = await memberships_repository.create_membership(
        session, organization_id=organization_id, user_id=user.id, role=role
    )
    choices = modules_from_rows(invitation.module_permissions)
    await module_permissions_repository.replace_for_membership(
        session,
        organization_id=organization_id,
        membership_id=membership.id,
        modules={module.value: level.value for module, level in choices.items()},
    )
    await invitations_repository.mark_accepted(session, invitation)
    effective = modules_for(role.value, choices)
    await audit_service.record(
        session,
        organization_id=organization_id,
        actor_user_id=user.id,
        action="invitation.accepted",
        resource_type="invitation",
        resource_id=str(invitation.id),
        payload={
            "email": user.email,
            "role": role.value,
            "modules": modules_to_plain(effective),
        },
    )
    return AcceptInvitationResponse(organization_id=organization_id, role=role, modules=effective)
