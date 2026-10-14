"""Service du tableau de bord personnalisable (SPEC §4).

Deux responsabilités, aucune logique dans le routeur :

- **Le catalogue** des widgets disponibles, filtré par les droits du membre selon le
  même principe que le Pouls : un KPI n'est proposé que si son module est visible,
  le fil d'activité est réservé aux administrateurs, la santé et les objectifs sont
  toujours proposés.
- **La mise en page** personnelle : chaque membre range ses widgets comme il veut ;
  elle est enregistrée pour lui seul (une ligne par couple organisation/utilisateur)
  et remise à zéro à la demande. Un widget enregistré puis devenu interdit (droit
  retiré, rôle revu) est écarté à la lecture — défense en profondeur.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import modules_for
from app.models.enums import Module, PermissionLevel, Role
from app.models.membership import Membership
from app.repositories import dashboard_layouts as dashboard_layouts_repository
from app.repositories import module_permissions as module_permissions_repository
from app.schemas.dashboard import (
    GRID_COLUMNS,
    DashboardLayoutUpdate,
    DashboardOut,
    DashboardPlacement,
    DashboardWidgetOut,
    WidgetKind,
)
from app.schemas.metrics import metric_prefix
from app.services import audit as audit_service
from app.services.errors import ServiceProblem
from app.services.pulse import PULSE_KPI_KEYS

# Identifiants des widgets non-KPI ; un KPI porte le préfixe `kpi.<clé canonique>`.
WIDGET_HEALTH = "health"
WIDGET_GOALS = "goals"
WIDGET_ACTIVITY = "activity"
KPI_WIDGET_PREFIX = "kpi."

# Géométrie de la disposition par défaut, sur une grille à 12 colonnes.
_KPI_PER_ROW = 3
_KPI_WIDTH = 4
_KPI_HEIGHT = 2
_HEALTH_HEIGHT = 2
_PANEL_WIDTH = 6
_PANEL_HEIGHT = 6


def _kpi_widget_id(metric_key: str) -> str:
    """Identifiant de widget d'un KPI clé (ex. `kpi.finance.revenue`)."""
    return f"{KPI_WIDGET_PREFIX}{metric_key}"


def _full_catalog() -> list[DashboardWidgetOut]:
    """Catalogue complet (indépendant des droits) : définit les widgets connus."""
    widgets = [DashboardWidgetOut(widget_id=WIDGET_HEALTH, kind=WidgetKind.HEALTH)]
    for metric_key in PULSE_KPI_KEYS:
        widgets.append(
            DashboardWidgetOut(
                widget_id=_kpi_widget_id(metric_key),
                kind=WidgetKind.KPI,
                module=Module(metric_prefix(metric_key)),
                metric_key=metric_key,
            )
        )
    widgets.append(DashboardWidgetOut(widget_id=WIDGET_GOALS, kind=WidgetKind.GOALS))
    widgets.append(DashboardWidgetOut(widget_id=WIDGET_ACTIVITY, kind=WidgetKind.ACTIVITY))
    return widgets


async def _visible_modules(
    session: AsyncSession, membership: Membership
) -> dict[Module, PermissionLevel]:
    """Modules visibles du membre : stocké, ou `edit` partout pour un admin."""
    rows = await module_permissions_repository.list_for_membership(
        session, membership_id=membership.id
    )
    choices = {Module(row.module): PermissionLevel(row.level) for row in rows}
    return modules_for(membership.role, choices)


def _is_admin(membership: Membership) -> bool:
    return membership.role == Role.ADMIN.value


def _catalog(modules: dict[Module, PermissionLevel], *, is_admin: bool) -> list[DashboardWidgetOut]:
    """Catalogue filtré par les droits : KPI des modules visibles, activité admin."""
    allowed: list[DashboardWidgetOut] = []
    for widget in _full_catalog():
        if widget.kind == WidgetKind.ACTIVITY:
            if not is_admin:
                continue
        elif widget.kind == WidgetKind.KPI:
            assert widget.module is not None  # invariante du catalogue
            if modules.get(widget.module, PermissionLevel.NONE) == PermissionLevel.NONE:
                continue
        allowed.append(widget)
    return allowed


def _default_placements(catalog: list[DashboardWidgetOut]) -> list[DashboardPlacement]:
    """Disposition par défaut : santé en bandeau, KPI par trois, puis les panneaux."""
    health = next(widget for widget in catalog if widget.kind == WidgetKind.HEALTH)
    kpis = [widget for widget in catalog if widget.kind == WidgetKind.KPI]
    panels = [
        widget for widget in catalog if widget.kind in (WidgetKind.GOALS, WidgetKind.ACTIVITY)
    ]

    placements = [
        DashboardPlacement(widget_id=health.widget_id, x=0, y=0, w=GRID_COLUMNS, h=_HEALTH_HEIGHT)
    ]
    for index, widget in enumerate(kpis):
        row, column = divmod(index, _KPI_PER_ROW)
        placements.append(
            DashboardPlacement(
                widget_id=widget.widget_id,
                x=column * _KPI_WIDTH,
                y=_HEALTH_HEIGHT + row * _KPI_HEIGHT,
                w=_KPI_WIDTH,
                h=_KPI_HEIGHT,
            )
        )
    kpi_rows = -(-len(kpis) // _KPI_PER_ROW)  # arrondi au supérieur
    panel_y = _HEALTH_HEIGHT + kpi_rows * _KPI_HEIGHT
    for index, widget in enumerate(panels):
        placements.append(
            DashboardPlacement(
                widget_id=widget.widget_id,
                x=index * _PANEL_WIDTH,
                y=panel_y,
                w=_PANEL_WIDTH,
                h=_PANEL_HEIGHT,
            )
        )
    return placements


async def get_layout(session: AsyncSession, membership: Membership) -> DashboardOut:
    """Mise en page du membre (enregistrée ou par défaut) et catalogue autorisé."""
    modules = await _visible_modules(session, membership)
    catalog = _catalog(modules, is_admin=_is_admin(membership))
    row = await dashboard_layouts_repository.get_for_user(
        session, organization_id=membership.organization_id, user_id=membership.user_id
    )
    if row is None:
        return DashboardOut(
            available_widgets=catalog,
            layout=_default_placements(catalog),
            is_default=True,
        )
    allowed_ids = {widget.widget_id for widget in catalog}
    layout = [
        DashboardPlacement(**placement)
        for placement in row.widgets
        if placement.get("widget_id") in allowed_ids
    ]
    return DashboardOut(available_widgets=catalog, layout=layout, is_default=False)


async def save_layout(
    session: AsyncSession, *, membership: Membership, payload: DashboardLayoutUpdate
) -> DashboardOut:
    """Enregistre la mise en page du membre ; refuse un widget inconnu ou interdit."""
    modules = await _visible_modules(session, membership)
    catalog = _catalog(modules, is_admin=_is_admin(membership))
    allowed_ids = {widget.widget_id for widget in catalog}
    known_ids = {widget.widget_id for widget in _full_catalog()}

    for placement in payload.widgets:
        if placement.widget_id not in known_ids:
            raise ServiceProblem(422, f"Widget inconnu : « {placement.widget_id} ».")
        if placement.widget_id not in allowed_ids:
            raise ServiceProblem(403, f"Widget non autorisé : « {placement.widget_id} ».")

    widgets = [placement.model_dump() for placement in payload.widgets]
    await dashboard_layouts_repository.upsert(
        session,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        widgets=widgets,
    )
    await audit_service.record(
        session,
        organization_id=membership.organization_id,
        actor_user_id=membership.user_id,
        action="dashboard.layout.updated",
        resource_type="dashboard_layout",
        resource_id=str(membership.user_id),
        payload={"widgets": [placement.widget_id for placement in payload.widgets]},
    )
    return DashboardOut(available_widgets=catalog, layout=list(payload.widgets), is_default=False)


async def reset_layout(session: AsyncSession, *, membership: Membership) -> None:
    """Supprime la mise en page du membre (retour au défaut) ; journalise si effet."""
    deleted = await dashboard_layouts_repository.delete_for_user(
        session, organization_id=membership.organization_id, user_id=membership.user_id
    )
    if not deleted:
        return
    await audit_service.record(
        session,
        organization_id=membership.organization_id,
        actor_user_id=membership.user_id,
        action="dashboard.layout.reset",
        resource_type="dashboard_layout",
        resource_id=str(membership.user_id),
    )
