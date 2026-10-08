"""Repository : utilisateurs (accès aux données uniquement, aucune règle métier)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def create_user(session: AsyncSession, *, email: str, password_hash: str | None) -> User:
    """Insère un compte. `password_hash` est None pour un compte Google OIDC."""
    user = User(email=email.lower(), password_hash=password_hash)
    session.add(user)
    await session.flush()
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Retourne le compte portant cet e-mail (normalisé en minuscules), ou None."""
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()
