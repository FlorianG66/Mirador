"""Repository : module_permissions (niveaux none / view / edit par membership)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module_permission import ModulePermission


async def get_level(session: AsyncSession, *, membership_id: uuid.UUID, module: str) -> str | None:
    """Niveau stocké pour un module, ou None si aucune ligne (donc `none`)."""
    result = await session.execute(
        select(ModulePermission.level).where(
            ModulePermission.membership_id == membership_id,
            ModulePermission.module == module,
        )
    )
    return result.scalar_one_or_none()


async def list_for_membership(
    session: AsyncSession, *, membership_id: uuid.UUID
) -> list[ModulePermission]:
    """Lignes de permission d'un membership, triées par module (réponse stable)."""
    result = await session.execute(
        select(ModulePermission)
        .where(ModulePermission.membership_id == membership_id)
        .order_by(ModulePermission.module)
    )
    return list(result.scalars().all())


async def replace_for_membership(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    modules: dict[str, str],
) -> None:
    """Remplace l'ensemble des niveaux : ce qui n'est pas renvoyé retombe à `none`.

    Les lignes `none` ne sont pas stockées : leur absence vaut `none`.
    """
    await session.execute(
        delete(ModulePermission).where(ModulePermission.membership_id == membership_id)
    )
    session.add_all(
        [
            ModulePermission(
                organization_id=organization_id,
                membership_id=membership_id,
                module=module,
                level=level,
            )
            for module, level in modules.items()
            if level != "none"
        ]
    )
    await session.flush()
