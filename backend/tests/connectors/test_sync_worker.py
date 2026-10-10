"""Tests du worker de synchronisation (phase 4c).

Le worker doit parcourir toutes les organisations, synchroniser chacune dans sa
propre session (tenant posé, commit), isoler un échec par organisation et ne
jamais s'arrêter sur la première erreur.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.tenancy import set_tenant
from app.workers import sync as sync_worker_module
from app.workers.sync import sync_all_organizations
from tests.conftest import seed_organization_with_admin


async def _sample_org(session: AsyncSession, *, name: str, email: str) -> uuid.UUID:
    """Crée une organisation + admin en base, commitée (sans poser de tenant)."""
    organization_id, _ = await seed_organization_with_admin(session, name=name, email=email)
    await session.commit()
    return organization_id


async def _count_snapshots(
    session_factory: async_sessionmaker[AsyncSession], organization_id: uuid.UUID
) -> int:
    """Compte les snapshots d'une organisation (en passant par la RLS réelle)."""
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        result = await session.execute(
            text("SELECT count(*) FROM metric_snapshots WHERE organization_id = :org"),
            {"org": organization_id},
        )
        return int(result.scalar_one())


@pytest.mark.asyncio
async def test_worker_synchronise_toutes_les_organisations(
    db_session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    org_a = await _sample_org(db_session, name="Worker A", email="worker-a@example.com")
    org_b = await _sample_org(db_session, name="Worker B", email="worker-b@example.com")

    await sync_all_organizations(session_factory)

    assert await _count_snapshots(session_factory, org_a) > 0
    assert await _count_snapshots(session_factory, org_b) > 0


@pytest.mark.asyncio
async def test_worker_est_idempotent(
    db_session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    org = await _sample_org(db_session, name="Worker I", email="worker-i@example.com")

    await sync_all_organizations(session_factory)
    first_count = await _count_snapshots(session_factory, org)
    assert first_count > 0

    await sync_all_organizations(session_factory)
    assert await _count_snapshots(session_factory, org) == first_count


@pytest.mark.asyncio
async def test_echec_d_une_organisation_n_arrete_pas_les_autres(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    org_broken = await _sample_org(db_session, name="Worker KO", email="worker-ko@example.com")
    org_healthy = await _sample_org(db_session, name="Worker OK", email="worker-ok@example.com")

    original = sync_worker_module.sync_organization

    async def _flaky(session: AsyncSession, organization_id: uuid.UUID) -> int:
        if organization_id == org_broken:
            raise RuntimeError("panne volontaire du connecteur")
        return await original(session, organization_id)

    monkeypatch.setattr(sync_worker_module, "sync_organization", _flaky)

    await sync_all_organizations(session_factory)  # ne doit pas lever

    assert await _count_snapshots(session_factory, org_broken) == 0
    assert await _count_snapshots(session_factory, org_healthy) > 0


@pytest.mark.asyncio
async def test_worker_sans_organisation_ne_leve_pas(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sync_all_organizations(session_factory)
