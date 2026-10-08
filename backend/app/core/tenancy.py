"""Isolation multi-tenant : paramètres de session PostgreSQL qui pilotent la Row-Level Security."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Lus par les politiques RLS de la migration 0002 (NULLIF les ramène à NULL si vides).
USER_TENANT_GUC = "app.current_user_id"
ORGANIZATION_TENANT_GUC = "app.current_organization_id"


async def set_tenant(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
) -> None:
    """Pose l'utilisateur et l'organisation courants pour la transaction en cours.

    Les deux paramètres sont toujours réécrits : un paramètre omis est effacé, jamais
    hérité d'une requête précédente. La valeur est locale à la transaction (is_local),
    donc purgée au commit — c'est elle qui alimente les politiques RLS.
    """
    await session.execute(
        text(
            "SELECT set_config(:user_key, :user_value, true),"
            " set_config(:organization_key, :organization_value, true)"
        ),
        {
            "user_key": USER_TENANT_GUC,
            "user_value": str(user_id) if user_id is not None else "",
            "organization_key": ORGANIZATION_TENANT_GUC,
            "organization_value": str(organization_id) if organization_id is not None else "",
        },
    )
