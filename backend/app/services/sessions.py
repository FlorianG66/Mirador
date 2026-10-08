"""Service de session : émission, rotation et révocation des jetons d'authentification."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    ACCESS_TOKEN_TTL_SECONDS,
    REFRESH_TOKEN_TTL_SECONDS,
    generate_token,
    hash_token,
)
from app.models.session import UserSession
from app.repositories import sessions as sessions_repository

# Le CSRF ne change qu'à la création : il appartient à la session, pas à l'accès.


@dataclass(frozen=True)
class IssuedSession:
    """Les valeurs brutes à mettre dans les cookies, liées à une session."""

    user_id: uuid.UUID
    access_token: str
    refresh_token: str
    csrf_token: str


def _expires_at(seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


async def issue_session(session: AsyncSession, *, user_id: uuid.UUID) -> IssuedSession:
    """Crée une session et retourne les trois jetons à distribuer au navigateur."""
    access_token, refresh_token, csrf_token = (
        generate_token(),
        generate_token(),
        generate_token(),
    )
    await sessions_repository.create_session(
        session,
        user_id=user_id,
        access_token_hash=hash_token(access_token),
        refresh_token_hash=hash_token(refresh_token),
        csrf_token=csrf_token,
        access_expires_at=_expires_at(ACCESS_TOKEN_TTL_SECONDS),
        refresh_expires_at=_expires_at(REFRESH_TOKEN_TTL_SECONDS),
    )
    return IssuedSession(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
    )


async def rotate_session(session: AsyncSession, *, refresh_token: str) -> IssuedSession | None:
    """Remplace les deux jetons si le rafraîchissement est valide, sinon None.

    Un ancien rafraîchissement rejoué échoue : la rotation le rend inutilisable.
    """
    row = await sessions_repository.get_by_refresh_hash(session, hash_token(refresh_token))
    now = datetime.now(UTC)
    if row is None or row.revoked_at is not None or row.refresh_expires_at <= now:
        return None
    access_token, refresh_token_new = generate_token(), generate_token()
    await sessions_repository.rotate(
        session,
        row,
        access_token_hash=hash_token(access_token),
        refresh_token_hash=hash_token(refresh_token_new),
        access_expires_at=_expires_at(ACCESS_TOKEN_TTL_SECONDS),
        refresh_expires_at=_expires_at(REFRESH_TOKEN_TTL_SECONDS),
    )
    return IssuedSession(
        user_id=row.user_id,
        access_token=access_token,
        refresh_token=refresh_token_new,
        csrf_token=row.csrf_token,
    )


async def revoke_session(session: AsyncSession, *, row: UserSession) -> None:
    """Révoque la session (déconnexion) : ses jetons deviennent invalides."""
    await sessions_repository.revoke(session, row)
