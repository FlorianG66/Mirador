"""Service des notifications in-app (phase 6c-ii).

Déclenche des notifications depuis les événements déjà produits :
- Objectifs : `goal.achieved` et `goal.off_track` (via `services.goals`).
- Fiche légale : `legal.diverged` au rafraîchissement du registre.

Les règles d'alerte configurables (`alert_rules`) arrivent en 6c-iii : ici, seuls
les événements existants génèrent des notifications. Aucun texte n'est figé ici :
`kind` est une clé i18n et `params` porte de quoi l'interpoler côté frontend.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import modules_for
from app.models.enums import Module, PermissionLevel, Role
from app.repositories import memberships as memberships_repository
from app.repositories import module_permissions as module_permissions_repository
from app.repositories import notifications as notifications_repository
from app.schemas.goals import GoalStatus
from app.schemas.metrics import metric_prefix
from app.services import goals as goals_service

#: Route frontend associée au module concerné (cible du clic sur la notification).
_MODULE_LINKS: dict[str, str] = {
    "web": "/web",
    "social": "/social",
    "projects": "/projects",
    "legal": "/legal",
    "finance": "/finance",
}


async def _admins_and_editors_on(
    session: AsyncSession, organization_id: uuid.UUID, module: Module
) -> list[uuid.UUID]:
    members = await memberships_repository.list_members(session, organization_id=organization_id)
    recipients: list[uuid.UUID] = []
    for member in members:
        if member.role == Role.ADMIN:
            recipients.append(member.user_id)
            continue
        perms = await module_permissions_repository.list_for_membership(
            session, membership_id=member.id
        )
        choices = {Module(p.module): PermissionLevel(p.level) for p in perms}
        effective = modules_for(member.role, choices)
        if effective.get(module, PermissionLevel.NONE) == PermissionLevel.EDIT:
            recipients.append(member.user_id)
    return recipients


async def evaluate_goal_notifications(session: AsyncSession, organization_id: uuid.UUID) -> None:
    """Émet les notifications d'objectif (atteint / en dérive) pour une organisation.

    Idempotent : une notification non lue déjà émise pour le même objectif et le
    même état n'est jamais dupliquée (`dedup_key`). Les destinataires sont les
    administrateurs et les membres ayant `edit` sur le module de l'objectif.
    """
    for goal, progress in await goals_service.list_goals_with_progress(session, organization_id):
        if progress.status == GoalStatus.ACHIEVED:
            kind = "goal.achieved"
            dedup = f"goal:{goal.id}:achieved"
        elif progress.status == GoalStatus.OFF_TRACK:
            kind = "goal.off_track"
            dedup = f"goal:{goal.id}:off_track"
        else:
            continue
        prefix = metric_prefix(goal.metric_key)
        link = _MODULE_LINKS.get(prefix, f"/{prefix}")
        recipients = await _admins_and_editors_on(session, organization_id, Module(prefix))
        for uid in recipients:
            existing = await notifications_repository.get_existing_dedup(
                session, organization_id=organization_id, user_id=uid, dedup_key=dedup
            )
            if existing:
                continue
            await notifications_repository.create_notification(
                session,
                organization_id=organization_id,
                user_id=uid,
                kind=kind,
                params={
                    "metric_key": goal.metric_key,
                    "target_value": goal.target_value,
                    "period_days": goal.period_days,
                    "direction": goal.direction,
                },
                link=link,
                dedup_key=dedup,
            )


async def notify_legal_diverged(
    session: AsyncSession, organization_id: uuid.UUID, diverged_fields: list[dict[str, object]]
) -> None:
    """Notifie les administrateurs qu'une valeur manuelle diverge du registre.

    Une seule notification non lue par administrateur : les écarts suivants
    mettent à jour les champs concernés au lieu d'empiler des doublons.
    """
    members = await memberships_repository.list_members(session, organization_id=organization_id)
    for member in members:
        if member.role != Role.ADMIN:
            continue
        dedup = f"legal:diverged:unread:{organization_id}:{member.user_id}"
        existing = await notifications_repository.get_existing_dedup(
            session,
            organization_id=organization_id,
            user_id=member.user_id,
            dedup_key=dedup,
        )
        if existing is not None:
            existing.params = {"fields": diverged_fields}
            existing.link = "/legal"
            await session.flush()
            continue
        await notifications_repository.create_notification(
            session,
            organization_id=organization_id,
            user_id=member.user_id,
            kind="legal.diverged",
            params={"fields": diverged_fields},
            link="/legal",
            dedup_key=dedup,
        )
