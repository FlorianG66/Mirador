"""Dépendances FastAPI injectées dans les routes (session, tenant, authentification)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.constants import ACCESS_COOKIE
from app.core.security import hash_token
from app.core.tenancy import set_tenant
from app.models.session import UserSession
from app.models.user import User
from app.repositories import sessions as sessions_repository
from app.services.legal_registry import LegalRegistry


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Une session SQLAlchemy par requête : commit en fin de succès, rollback sinon.

    Une seule transaction couvre toute la requête : le tenant posé par `set_tenant`
    reste valable jusqu'au commit final (aucun commit intermédiaire autorisé).
    """
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    session = factory()
    # Tenant neutre tant que la route n'a pas authentifié : aucun rôle par défaut.
    await set_tenant(session)
    try:
        yield session
    except BaseException:
        await session.rollback()
        raise
    else:
        await session.commit()
    finally:
        await session.close()


def get_request_settings(request: Request) -> Settings:
    """Récupère les settings portés par l'application (permet de les injecter en test)."""
    settings: Settings = request.app.state.settings
    return settings


def get_legal_registry(request: Request) -> LegalRegistry:
    """Registre d'identité légale porté par l'application (transport injectable en test)."""
    registry: LegalRegistry = request.app.state.legal_registry
    return registry


async def get_current_session(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserSession:
    """Session valide derrière le cookie d'accès : révoquée ou expirée → 401."""
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(401, "Authentification requise.")
    row = await sessions_repository.get_by_access_hash(session, hash_token(token))
    if row is None or row.revoked_at is not None or row.access_expires_at <= datetime.now(UTC):
        raise HTTPException(401, "Session expirée ou invalide.")
    return row


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_session: Annotated[UserSession, Depends(get_current_session)],
) -> User:
    """Utilisateur derrière la session ; pose le tenant utilisateur pour la RLS.

    `memberships` est lisible avec le seul utilisateur (politique `USING`) : c'est
    ce qui permet à `/auth/me` de lister les rattachements avant tout choix
    d'organisation active.
    """
    user = await session.get(User, current_session.user_id)
    if user is None:
        raise HTTPException(401, "Session expirée ou invalide.")
    await set_tenant(session, user_id=user.id)
    return user
