"""Service du Pouls (phase 5f) : agrégat de la page d'accueil.

Le Pouls ne calcule aucune règle métier : il rassemble les KPI clés déjà
stockés par les connecteurs (démo comprise), restreints aux modules que le
membre peut voir, puis résume la santé d'exploitation (« un module a-t-il de la
donnée ? »). Les alertes et objectifs réels viendront en phase 6.
"""

from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import modules_for
from app.models.enums import Module, PermissionLevel, Role
from app.models.membership import Membership
from app.repositories import metric_snapshots as metric_snapshots_repository
from app.repositories import module_permissions as module_permissions_repository
from app.schemas.metrics import metric_prefix
from app.schemas.pulse import PulseHealthOut, PulseKpiOut, PulseOut
from app.services import audit as audit_service

# Modules couverts par un KPI clé du Pouls (le légal n'expose pas de métrique).
_KPI_MODULES: tuple[Module, ...] = (
    Module.FINANCE,
    Module.WEB,
    Module.SOCIAL,
    Module.PROJECTS,
)

# KPI clés affichés sur la page d'accueil, dans l'ordre des modules.
PULSE_KPI_KEYS: tuple[str, ...] = (
    "finance.revenue",
    "finance.margin",
    "web.visitors",
    "web.conversions",
    "social.followers",
    "social.engagement_rate",
    "projects.open_tasks",
    "projects.avg_progress",
)


async def _effective_modules(
    session: AsyncSession, membership: Membership
) -> dict[Module, PermissionLevel]:
    """Niveaux affichables du membre : stocké, ou `edit` partout pour un admin."""
    rows = await module_permissions_repository.list_for_membership(
        session, membership_id=membership.id
    )
    choices = {Module(row.module): PermissionLevel(row.level) for row in rows}
    return modules_for(membership.role, choices)


async def _build_kpis(
    session: AsyncSession,
    organization_id: uuid.UUID,
    modules: dict[Module, PermissionLevel],
) -> list[PulseKpiOut]:
    """KPI clés des modules visibles, avec la valeur précédente si elle existe.

    Un KPI sans donnée est omis : le module apparaîtra alors « sans donnée »
    dans la santé, plutôt qu'avec une valeur inventée.
    """
    kpis: list[PulseKpiOut] = []
    for metric_key in PULSE_KPI_KEYS:
        module = Module(metric_prefix(metric_key))
        if modules.get(module, PermissionLevel.NONE) == PermissionLevel.NONE:
            continue
        snapshots = await metric_snapshots_repository.get_latest(
            session, organization_id, metric_key, limit=2
        )
        if not snapshots:
            continue
        current = snapshots[0]
        previous = snapshots[1] if len(snapshots) > 1 else None
        kpis.append(
            PulseKpiOut(
                module=module,
                metric_key=metric_key,
                unit=current.unit,
                value=current.value,
                previous_value=previous.value if previous is not None else None,
                captured_at=current.captured_at,
            )
        )
    return kpis


def _build_health(
    modules: dict[Module, PermissionLevel], kpis: list[PulseKpiOut]
) -> PulseHealthOut:
    """Santé d'exploitation : modules visibles alimentés sur modules visibles.

    `unknown` quand aucun module à métrique n'est visible (rien à juger) ;
    `good` quand tous les modules visibles ont de la donnée ; `warning` dans
    l'intervalle. Aucune règle financière : c'est un état de connexion.
    """
    total = sum(
        1
        for module in _KPI_MODULES
        if modules.get(module, PermissionLevel.NONE) != PermissionLevel.NONE
    )
    with_data = len({kpi.module for kpi in kpis})
    status: Literal["good", "warning", "unknown"]
    if total == 0:
        status = "unknown"
    elif with_data == total:
        status = "good"
    else:
        status = "warning"
    return PulseHealthOut(status=status, modules_with_data=with_data, modules_total=total)


async def build_pulse(session: AsyncSession, *, membership: Membership) -> PulseOut:
    """Compose le Pouls de l'organisation active pour le membre courant."""
    modules = await _effective_modules(session, membership)
    kpis = await _build_kpis(session, membership.organization_id, modules)
    health = _build_health(modules, kpis)
    activity = (
        await audit_service.list_recent(session, organization_id=membership.organization_id)
        if membership.role == Role.ADMIN.value
        else []
    )
    return PulseOut(kpis=kpis, health=health, activity=activity)
