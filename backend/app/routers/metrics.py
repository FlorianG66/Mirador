"""Route de lecture des métriques canoniques (phase 4d) : générique, tenant + permissions.

Un seul endpoint expose n'importe quelle série stockée : `GET /metrics/{metric_key}`.
La permission est dérivée de la clé (le préfixe `module` de `module.metric`), donc
le niveau `view` du module correspondant est exigé.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.permissions import ensure_module_access, get_current_tenant
from app.models.enums import Module, PermissionLevel
from app.models.membership import Membership
from app.schemas.metrics import MetricComparison, MetricSeries, validate_metric_key
from app.services import metrics as metrics_service

router = APIRouter(prefix="/organizations/{organization_id}")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentTenant = Annotated[Membership, Depends(get_current_tenant)]


def require_metric_module(level: PermissionLevel) -> Callable[..., Awaitable[Membership]]:
    """Garde `view`/`edit` du module extrait de la clé canonique (SPEC §2, §5.4)."""

    async def dependency(
        metric_key: Annotated[str, Path(description="Clé canonique « module.metric »")],
        session: SessionDependency,
        membership: CurrentTenant,
    ) -> Membership:
        module = _module_from_key(metric_key)
        return await ensure_module_access(session, membership, module, level)

    return dependency


def _module_from_key(metric_key: str) -> Module:
    """Valide la clé (format canonique) et retourne le module qu'elle porte."""
    try:
        validate_metric_key(metric_key)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return Module(metric_key.partition(".")[0])


@router.get("/metrics/{metric_key}", response_model=MetricSeries)
async def read_metric(
    metric_key: Annotated[str, Path(description="Clé canonique « module.metric »")],
    session: SessionDependency,
    membership: Annotated[Membership, Depends(require_metric_module(PermissionLevel.VIEW))],
    start: Annotated[datetime | None, Query(description="Borne basse inclusive")] = None,
    end: Annotated[datetime | None, Query(description="Borne haute inclusive")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> MetricSeries:
    """Série chronologique d'une métrique, pour l'organisation active de l'utilisateur."""
    return await metrics_service.get_metric_series(
        session,
        organization_id=membership.organization_id,
        metric_key=metric_key,
        start=start,
        end=end,
        limit=limit,
    )


@router.get("/metrics/{metric_key}/comparison", response_model=MetricComparison)
async def read_metric_comparison(
    metric_key: Annotated[str, Path(description="Clé canonique « module.metric »")],
    session: SessionDependency,
    membership: Annotated[Membership, Depends(require_metric_module(PermissionLevel.VIEW))],
    days: Annotated[int, Query(ge=1, le=365, description="Longueur de la fenêtre en jours")] = 30,
    end: Annotated[
        datetime | None, Query(description="Borne haute ; maintenant par défaut")
    ] = None,
) -> MetricComparison:
    """Série sur `days` jours comparée aux `days` jours précédents (SPEC §4)."""
    return await metrics_service.get_metric_comparison(
        session,
        organization_id=membership.organization_id,
        metric_key=metric_key,
        days=days,
        end=end,
    )
