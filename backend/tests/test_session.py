"""Dépendance de session SQLAlchemy : une transaction par requête, commit ou rollback."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request

from app.core.deps import get_session
from app.core.tenancy import ORGANIZATION_TENANT_GUC, USER_TENANT_GUC
from app.models.organization import Organization
from app.repositories import organizations as organizations_repository
from tests.conftest import build_request, current_setting


def _session_factory(app: FastAPI) -> async_sessionmaker[AsyncSession]:
    """Fabrique portée par l'application (créée par create_app)."""
    factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    return factory


async def test_get_session_starts_from_a_neutral_tenant(app: FastAPI) -> None:
    """Aucune requête ne démarre avec un tenant hérité d'une connexion recyclée du pool."""
    request: Request = build_request(app)
    generator = get_session(request)
    session = await anext(generator)

    assert await current_setting(session, ORGANIZATION_TENANT_GUC) in (None, "")
    assert await current_setting(session, USER_TENANT_GUC) in (None, "")

    await generator.aclose()


async def test_get_session_commits_the_work_of_the_request(app: FastAPI) -> None:
    request: Request = build_request(app)
    generator = get_session(request)
    session = await anext(generator)
    organization = await organizations_repository.create_organization(session, name="À vérifier")

    with pytest.raises(StopAsyncIteration):
        await generator.asend(None)

    async with _session_factory(app)() as check:
        stored = await organizations_repository.get_organization(check, organization.id)
        assert stored is not None
        assert stored.name == "À vérifier"
        await check.execute(delete(Organization).where(Organization.id == organization.id))
        await check.commit()


async def test_get_session_rolls_back_when_the_request_fails(app: FastAPI) -> None:
    request: Request = build_request(app)
    generator = get_session(request)
    session = await anext(generator)
    await organizations_repository.create_organization(session, name="Jamais écrite")

    with pytest.raises(RuntimeError, match="échec simulé"):
        await generator.athrow(RuntimeError("échec simulé"))

    async with _session_factory(app)() as check:
        result = await check.execute(
            select(Organization).where(Organization.name == "Jamais écrite")
        )
        assert result.scalar_one_or_none() is None
