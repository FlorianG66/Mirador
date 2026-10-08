"""Dépendances FastAPI injectées dans les routes (session, puis tenant et auth en phase 2b)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.tenancy import set_tenant


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
