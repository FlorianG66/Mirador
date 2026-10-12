"""Service des objectifs et budgets (SPEC §4) : cible, progression, alerte de dérive.

Règles portées ici (aucune logique dans le routeur) :

- **La progression se recalcule**, elle ne se stocke pas : on agrège la métrique
  visée sur une fenêtre glissante de `period_days` selon le catalogue
  (`app.services.metric_catalog`), puis on la rapporte à la cible.
- **L'alerte de dérive** se juge par comparaison à la fenêtre précédente
  équivalente : la cible n'est pas atteinte *et* la métrique s'en éloigne. Une
  métrique stable mais sous la cible reste « en cours » (`on_track`) ; aucune
  donnée donne `unknown` (module pas encore synchronisé).
- **La permission suit le module de la métrique** : `edit` pour créer, modifier ou
  supprimer ; la lecture ne montre que les objectifs des modules visibles (même
  règle que le Pouls).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import ensure_module_access, modules_for
from app.models.enums import GoalDirection, Module, PermissionLevel
from app.models.goal import Goal
from app.models.membership import Membership
from app.repositories import goals as goals_repository
from app.repositories import metric_snapshots as metric_snapshots_repository
from app.repositories import module_permissions as module_permissions_repository
from app.schemas.goals import GoalCreate, GoalOut, GoalProgress, GoalStatus, GoalUpdate
from app.schemas.metrics import metric_prefix
from app.services import audit as audit_service
from app.services.errors import ServiceProblem
from app.services.metric_catalog import aggregation_for, reduce_values


def _now() -> datetime:
    return datetime.now(UTC)


def _module_of(goal: Goal) -> Module:
    """Module porté par la clé canonique de l'objectif (préfixe `module.metric`)."""
    return Module(metric_prefix(goal.metric_key))


async def _effective_modules(
    session: AsyncSession, membership: Membership
) -> dict[Module, PermissionLevel]:
    """Modules visibles du membre : stocké, ou `edit` partout pour un admin."""
    rows = await module_permissions_repository.list_for_membership(
        session, membership_id=membership.id
    )
    choices = {Module(row.module): PermissionLevel(row.level) for row in rows}
    return modules_for(membership.role, choices)


def _progress_percent(current_value: float, target_value: float) -> float | None:
    """Part de la cible atteinte (ou consommée) en pourcentage ; `None` si cible nulle."""
    if target_value == 0:
        return None
    return round(current_value / target_value * 100, 2)


def _status(goal: Goal, current_value: float, previous_value: float) -> GoalStatus:
    """Statut de l'objectif : atteint, en cours, en dérive (éloignement du précédent)."""
    at_least = goal.direction == GoalDirection.AT_LEAST.value
    reached = current_value >= goal.target_value if at_least else current_value <= goal.target_value
    if reached:
        return GoalStatus.ACHIEVED
    moving_away = current_value < previous_value if at_least else current_value > previous_value
    return GoalStatus.OFF_TRACK if moving_away else GoalStatus.ON_TRACK


async def _progress(session: AsyncSession, organization_id: uuid.UUID, goal: Goal) -> GoalProgress:
    """Progression de l'objectif sur sa fenêtre glissante, comparée à la précédente."""
    aggregation = aggregation_for(goal.metric_key)
    window_end = _now()
    current_start = window_end - timedelta(days=goal.period_days)
    window_start = current_start - timedelta(days=goal.period_days)
    snapshots = await metric_snapshots_repository.get_series(
        session,
        organization_id,
        goal.metric_key,
        start=window_start,
        end=window_end,
        limit=goal.period_days * 2 + 10,
    )
    if not snapshots:
        return GoalProgress(status=GoalStatus.UNKNOWN)
    current_snapshots = [row for row in snapshots if row.captured_at > current_start]
    previous_snapshots = [row for row in snapshots if row.captured_at <= current_start]
    current_value = reduce_values([row.value for row in current_snapshots], aggregation)
    previous_value = reduce_values([row.value for row in previous_snapshots], aggregation)
    return GoalProgress(
        current_value=round(current_value, 2),
        previous_value=round(previous_value, 2),
        progress_percent=_progress_percent(current_value, goal.target_value),
        status=_status(goal, current_value, previous_value),
        unit=snapshots[-1].unit,
    )


async def _to_out(session: AsyncSession, organization_id: uuid.UUID, goal: Goal) -> GoalOut:
    """Assemble la réponse publique d'un objectif (définition + progression)."""
    return GoalOut(
        id=goal.id,
        metric_key=goal.metric_key,
        label=goal.label,
        direction=GoalDirection(goal.direction),
        target_value=goal.target_value,
        period_days=goal.period_days,
        progress=await _progress(session, organization_id, goal),
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


async def list_goals(session: AsyncSession, membership: Membership) -> list[GoalOut]:
    """Objectifs des modules visibles, avec leur progression (aucun refus possible)."""
    organization_id = membership.organization_id
    rows = await goals_repository.list_for_organization(session, organization_id)
    modules = await _effective_modules(session, membership)
    visible: list[GoalOut] = []
    for goal in rows:
        if modules.get(_module_of(goal), PermissionLevel.NONE) == PermissionLevel.NONE:
            continue
        visible.append(await _to_out(session, organization_id, goal))
    return visible


async def create_goal(
    session: AsyncSession, *, membership: Membership, payload: GoalCreate
) -> GoalOut:
    """Crée un objectif ; exige `edit` sur le module de la métrique visée."""
    await ensure_module_access(
        session, membership, Module(metric_prefix(payload.metric_key)), PermissionLevel.EDIT
    )
    goal = goals_repository.create(
        session,
        organization_id=membership.organization_id,
        metric_key=payload.metric_key,
        label=payload.label,
        direction=payload.direction,
        target_value=payload.target_value,
        period_days=payload.period_days,
    )
    await session.flush()
    await session.refresh(goal)
    await audit_service.record(
        session,
        organization_id=membership.organization_id,
        actor_user_id=membership.user_id,
        action="goal.created",
        resource_type="goal",
        resource_id=str(goal.id),
        payload={"metric_key": goal.metric_key, "direction": goal.direction},
    )
    return await _to_out(session, membership.organization_id, goal)


async def _get_or_404(
    session: AsyncSession, organization_id: uuid.UUID, goal_id: uuid.UUID
) -> Goal:
    goal = await goals_repository.get_by_id(session, organization_id, goal_id)
    if goal is None:
        raise ServiceProblem(404, "Objectif introuvable.")
    return goal


async def update_goal(
    session: AsyncSession, *, membership: Membership, goal_id: uuid.UUID, payload: GoalUpdate
) -> GoalOut:
    """Met à jour un objectif ; exige `edit` sur son module (et le nouveau s'il change)."""
    goal = await _get_or_404(session, membership.organization_id, goal_id)
    await ensure_module_access(session, membership, _module_of(goal), PermissionLevel.EDIT)
    provided = payload.model_fields_set
    if "metric_key" in provided and payload.metric_key is not None:
        await ensure_module_access(
            session, membership, Module(metric_prefix(payload.metric_key)), PermissionLevel.EDIT
        )
        goal.metric_key = payload.metric_key
    if "label" in provided:
        goal.label = payload.label
    if "direction" in provided and payload.direction is not None:
        goal.direction = payload.direction.value
    if "target_value" in provided and payload.target_value is not None:
        goal.target_value = payload.target_value
    if "period_days" in provided and payload.period_days is not None:
        goal.period_days = payload.period_days
    goal.updated_at = _now()
    await session.flush()
    await audit_service.record(
        session,
        organization_id=membership.organization_id,
        actor_user_id=membership.user_id,
        action="goal.updated",
        resource_type="goal",
        resource_id=str(goal.id),
        payload={"fields": sorted(provided)},
    )
    return await _to_out(session, membership.organization_id, goal)


async def delete_goal(session: AsyncSession, *, membership: Membership, goal_id: uuid.UUID) -> None:
    """Supprime un objectif ; exige `edit` sur son module."""
    goal = await _get_or_404(session, membership.organization_id, goal_id)
    await ensure_module_access(session, membership, _module_of(goal), PermissionLevel.EDIT)
    await goals_repository.delete(session, goal)
    await audit_service.record(
        session,
        organization_id=membership.organization_id,
        actor_user_id=membership.user_id,
        action="goal.deleted",
        resource_type="goal",
        resource_id=str(goal.id),
        payload={"metric_key": goal.metric_key},
    )
