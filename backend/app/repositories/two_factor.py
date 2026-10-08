"""Repository : codes de secours A2F (accès aux données uniquement)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backup_code import BackupCode


async def delete_backup_codes_for_user(session: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Révoque tous les codes d'un compte (réémission ou désactivation)."""
    await session.execute(delete(BackupCode).where(BackupCode.user_id == user_id))


async def add_backup_codes(
    session: AsyncSession, *, user_id: uuid.UUID, code_hashes: list[str]
) -> None:
    """Insère les hachages des codes de secours nouvellement émis."""
    for code_hash in code_hashes:
        session.add(BackupCode(user_id=user_id, code_hash=code_hash))
    await session.flush()


async def get_backup_code_by_hash(session: AsyncSession, code_hash: str) -> BackupCode | None:
    result = await session.execute(select(BackupCode).where(BackupCode.code_hash == code_hash))
    return result.scalar_one_or_none()


async def mark_backup_code_used(session: AsyncSession, row: BackupCode) -> None:
    """Consomme le code : un code de secours ne sert qu'une fois."""
    await session.execute(
        update(BackupCode).where(BackupCode.id == row.id).values(used_at=func.now())
    )
