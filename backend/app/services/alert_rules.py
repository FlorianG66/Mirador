"""Service des règles d'alerte (SPEC §4, phase 6c-iii).

Une règle surveille une clé canonique sur une fenêtre glissante et se déclenche
quand la valeur agrégée franchit son seuil dans le sens choisi. Comme pour les
objectifs :

- **L'évaluation se recalcule**, elle ne se stocke pas : on agrège la métrique
  selon le catalogue (`app.services.metric_catalog`) puis on compare au seuil.
- **La permission suit le module de la métrique** : `edit` pour créer, modifier
  ou supprimer ; la lecture ne montre que les modules visibles (comme le Pouls).
- **L'émission est réservée au worker** : `evaluate_alert_rules` est appelé par le
  worker de synchronisation, jamais lors d'un `GET` (une alerte correspond à un
  état écrit). La déduplication des notifications réutilise le mécanisme du canal
  (`dedup_key` sur les non-lues, cf. 6c-ii).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import ensure_module_access, modules_for
from app.models.alert_rule import AlertRule
from app.models.enums import AlertComparison, Module, PermissionLevel
from app.models.membership import Membership
from app.repositories import alert_rules as alert_rules_repository
from app.repositories import metric_snapshots as metric_snapshots_repository
from app.repositories import module_permissions as module_permissions_repository
from app.repositories import notifications as notifications_repository
from app.schemas.alert_rules import AlertRuleCreate, AlertRuleOut, AlertRuleUpdate
from app.schemas.metrics import metric_prefix
from app.services import audit as audit_service
from app.services import notifications as notifications_service
from app.services.errors import ServiceProblem
from app.services.metric_catalog import aggregation_for, reduce_values


def _now() -> datetime:
    return datetime.now(UTC)


def _module_of(rule: AlertRule) -> Module:
    """Module porté par la clé canonique de la règle (préfixe `module.metric`)."""
    return Module(metric_prefix(rule.metric_key))


def _to_out(rule: AlertRule) -> AlertRuleOut:
    """Assemble la réponse publique d'une règle (aucun calcul de valeur ici)."""
    return AlertRuleOut(
        id=rule.id,
        metric_key=rule.metric_key,
        label=rule.label,
        comparison=AlertComparison(rule.comparison),
        threshold=rule.threshold,
        period_days=rule.period_days,
        enabled=rule.enabled,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


async def _effective_modules(
    session: AsyncSession, membership: Membership
) -> dict[Module, PermissionLevel]:
    """Modules visibles du membre : stocké, ou `edit` partout pour un admin."""
    rows = await module_permissions_repository.list_for_membership(
        session, membership_id=membership.id
    )
    choices = {Module(row.module): PermissionLevel(row.level) for row in rows}
    return modules_for(membership.role, choices)


def _is_triggered(comparison: AlertComparison, value: float, threshold: float) -> bool:
    """La valeur de la fenêtre franchit-elle le seuil dans le sens de la règle ?"""
    if comparison == AlertComparison.ABOVE:
        return value > threshold
    return value < threshold


async def _window_value(
    session: AsyncSession, organization_id: uuid.UUID, rule: AlertRule
) -> float | None:
    """Valeur agrégée de la métrique sur la fenêtre glissante ; `None` sans donnée."""
    window_end = _now()
    window_start = window_end - timedelta(days=rule.period_days)
    snapshots = await metric_snapshots_repository.get_series(
        session,
        organization_id,
        rule.metric_key,
        start=window_start,
        end=window_end,
        limit=rule.period_days + 10,
    )
    if not snapshots:
        return None
    return reduce_values([row.value for row in snapshots], aggregation_for(rule.metric_key))


async def list_alert_rules(session: AsyncSession, membership: Membership) -> list[AlertRuleOut]:
    """Règles des modules visibles (aucun refus possible)."""
    rows = await alert_rules_repository.list_for_organization(session, membership.organization_id)
    modules = await _effective_modules(session, membership)
    return [
        _to_out(rule)
        for rule in rows
        if modules.get(_module_of(rule), PermissionLevel.NONE) != PermissionLevel.NONE
    ]


async def create_alert_rule(
    session: AsyncSession, *, membership: Membership, payload: AlertRuleCreate
) -> AlertRuleOut:
    """Crée une règle ; exige `edit` sur le module de la métrique surveillée."""
    await ensure_module_access(
        session, membership, Module(metric_prefix(payload.metric_key)), PermissionLevel.EDIT
    )
    rule = alert_rules_repository.create(
        session,
        organization_id=membership.organization_id,
        metric_key=payload.metric_key,
        label=payload.label,
        comparison=payload.comparison,
        threshold=payload.threshold,
        period_days=payload.period_days,
        enabled=payload.enabled,
    )
    await session.flush()
    await session.refresh(rule)
    await audit_service.record(
        session,
        organization_id=membership.organization_id,
        actor_user_id=membership.user_id,
        action="alert_rule.created",
        resource_type="alert_rule",
        resource_id=str(rule.id),
        payload={"metric_key": rule.metric_key, "comparison": rule.comparison},
    )
    return _to_out(rule)


async def _get_or_404(
    session: AsyncSession, organization_id: uuid.UUID, rule_id: uuid.UUID
) -> AlertRule:
    rule = await alert_rules_repository.get_by_id(session, organization_id, rule_id)
    if rule is None:
        raise ServiceProblem(404, "Règle d'alerte introuvable.")
    return rule


async def update_alert_rule(
    session: AsyncSession, *, membership: Membership, rule_id: uuid.UUID, payload: AlertRuleUpdate
) -> AlertRuleOut:
    """Met à jour une règle ; exige `edit` sur son module (et le nouveau s'il change)."""
    rule = await _get_or_404(session, membership.organization_id, rule_id)
    await ensure_module_access(session, membership, _module_of(rule), PermissionLevel.EDIT)
    provided = payload.model_fields_set
    if "metric_key" in provided and payload.metric_key is not None:
        await ensure_module_access(
            session, membership, Module(metric_prefix(payload.metric_key)), PermissionLevel.EDIT
        )
        rule.metric_key = payload.metric_key
    if "label" in provided:
        rule.label = payload.label
    if "comparison" in provided and payload.comparison is not None:
        rule.comparison = payload.comparison.value
    if "threshold" in provided and payload.threshold is not None:
        rule.threshold = payload.threshold
    if "period_days" in provided and payload.period_days is not None:
        rule.period_days = payload.period_days
    if "enabled" in provided and payload.enabled is not None:
        rule.enabled = payload.enabled
    rule.updated_at = _now()
    await session.flush()
    await audit_service.record(
        session,
        organization_id=membership.organization_id,
        actor_user_id=membership.user_id,
        action="alert_rule.updated",
        resource_type="alert_rule",
        resource_id=str(rule.id),
        payload={"fields": sorted(provided)},
    )
    return _to_out(rule)


async def delete_alert_rule(
    session: AsyncSession, *, membership: Membership, rule_id: uuid.UUID
) -> None:
    """Supprime une règle ; exige `edit` sur son module."""
    rule = await _get_or_404(session, membership.organization_id, rule_id)
    await ensure_module_access(session, membership, _module_of(rule), PermissionLevel.EDIT)
    await alert_rules_repository.delete(session, rule)
    await audit_service.record(
        session,
        organization_id=membership.organization_id,
        actor_user_id=membership.user_id,
        action="alert_rule.deleted",
        resource_type="alert_rule",
        resource_id=str(rule.id),
        payload={"metric_key": rule.metric_key},
    )


async def evaluate_alert_rules(session: AsyncSession, organization_id: uuid.UUID) -> None:
    """Émet les notifications des règles franchies pour une organisation.

    Réservé au worker de synchronisation (jamais appelé depuis un `GET`).
    Idempotent : une notification non lue déjà émise pour la même règle n'est pas
    dupliquée (`dedup_key`). Les destinataires sont les administrateurs et les
    membres ayant `edit` sur le module de la métrique surveillée.
    """
    rules = await alert_rules_repository.list_for_organization(
        session, organization_id, enabled_only=True
    )
    for rule in rules:
        value = await _window_value(session, organization_id, rule)
        if value is None:
            continue
        comparison = AlertComparison(rule.comparison)
        if not _is_triggered(comparison, value, rule.threshold):
            continue
        module = _module_of(rule)
        recipients = await notifications_service.admins_and_editors_on(
            session, organization_id, module
        )
        dedup = f"alert_rule:{rule.id}:{comparison.value}"
        link = notifications_service.module_link(module)
        params = {
            "metric_key": rule.metric_key,
            "threshold": rule.threshold,
            "comparison": comparison.value,
            "period_days": rule.period_days,
            "value": round(value, 2),
        }
        for user_id in recipients:
            existing = await notifications_repository.get_existing_dedup(
                session, organization_id=organization_id, user_id=user_id, dedup_key=dedup
            )
            if existing is not None:
                existing.params = params
                existing.link = link
                await session.flush()
                continue
            await notifications_repository.create_notification(
                session,
                organization_id=organization_id,
                user_id=user_id,
                kind="alert.threshold",
                params=params,
                link=link,
                dedup_key=dedup,
            )
