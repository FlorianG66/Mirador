"""Service des notifications in-app (phase 6c-ii, étendu Web Push en 6c-iii-b).

Déclenche des notifications depuis les événements déjà produits :
- Objectifs : `goal.achieved` et `goal.off_track` (via `services.goals`).
- Fiche légale : `legal.diverged` au rafraîchissement du registre.
- Règles d'alerte : `alert.threshold` (via `services.alert_rules`).

Depuis la 6c-iii-b, chaque notification créée est aussi **poussée** (Web Push) vers
les abonnements du destinataire, via un `PushSender` injectable (faux en test,
`None` = canal désactivé). L'envoi est best-effort : il ne fait jamais échouer
l'écriture de la notification in-app. Aucun texte n'est figé ici : `kind` est une
clé i18n et `params` porte de quoi l'interpoler côté frontend ou service worker.
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
from app.services import push as push_service

#: Route frontend associée au module concerné (cible du clic sur la notification).
_MODULE_LINKS: dict[str, str] = {
    "web": "/web",
    "social": "/social",
    "projects": "/projects",
    "legal": "/legal",
    "finance": "/finance",
}


def module_link(module: Module) -> str:
    """Route frontend d'un module (cible du clic sur une notification)."""
    return _MODULE_LINKS.get(module.value, f"/{module.value}")


async def push_notification(
    session: AsyncSession,
    *,
    push_sender: push_service.PushSender | None,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    kind: str,
    params: dict[str, object],
    link: str | None,
) -> None:
    """Pousse une notification vers les abonnements d'un destinataire (best-effort).

    Ne lève jamais : un échec de Web Push ne doit pas empêcher l'écriture de la
    notification in-app, qui reste la source de vérité du canal.
    """
    try:
        await push_service.send_to_user(
            session,
            sender=push_sender,
            organization_id=organization_id,
            user_id=user_id,
            message=push_service.message_for(kind, params, link),
        )
    except Exception:
        # Journalisation ailleurs (service push) : on protège seulement la transaction.
        pass


async def admins_and_editors_on(
    session: AsyncSession, organization_id: uuid.UUID, module: Module
) -> list[uuid.UUID]:
    """Destinataires d'un événement de module : admins + membres ayant `edit`.

    Partagé par les notifications d'objectif (6c-ii) et les règles d'alerte
    (6c-iii) : une seule règle de destinataires pour tout le canal.
    """
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


async def evaluate_goal_notifications(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    push_sender: push_service.PushSender | None = None,
) -> None:
    """Émet les notifications d'objectif (atteint / en dérive) pour une organisation.

    Idempotent : une notification non lue déjà émise pour le même objectif et le
    même état n'est jamais dupliquée (`dedup_key`). Les destinataires sont les
    administrateurs et les membres ayant `edit` sur le module de l'objectif.
    Chaque notification nouvelle est aussi poussée (Web Push, best-effort).
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
        link = module_link(Module(prefix))
        recipients = await admins_and_editors_on(session, organization_id, Module(prefix))
        params = {
            "metric_key": goal.metric_key,
            "target_value": goal.target_value,
            "period_days": goal.period_days,
            "direction": goal.direction,
        }
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
                params=params,
                link=link,
                dedup_key=dedup,
            )
            await push_notification(
                session,
                push_sender=push_sender,
                organization_id=organization_id,
                user_id=uid,
                kind=kind,
                params=params,
                link=link,
            )


async def notify_legal_diverged(
    session: AsyncSession,
    organization_id: uuid.UUID,
    diverged_fields: list[dict[str, object]],
    *,
    push_sender: push_service.PushSender | None = None,
) -> None:
    """Notifie les administrateurs qu'une valeur manuelle diverge du registre.

    Une seule notification non lue par administrateur : les écarts suivants
    mettent à jour les champs concernés au lieu d'empiler des doublons. Seules
    les notifications nouvelles sont poussées (une mise à jour n'a pas à rappeler
    l'attention deux fois).
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
        await push_notification(
            session,
            push_sender=push_sender,
            organization_id=organization_id,
            user_id=member.user_id,
            kind="legal.diverged",
            params={"fields": diverged_fields},
            link="/legal",
        )
