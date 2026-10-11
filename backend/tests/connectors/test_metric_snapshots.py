"""Tests d'intégration des snapshots de métriques (phase 4b).

Vérifie : la synchronisation remplit bien les quatre modules, son caractère
idempotent (re-synchronisation sans doublon), la dérivation déterministe du seed,
et l'isolation entre organisations (double filtre : repository + RLS réelle).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.tenancy import set_tenant
from app.repositories import metric_snapshots as metric_snapshots_repository
from app.services.sync import seed_for_organization, sync_organization
from tests.conftest import seed_organization_with_admin

EXPECTED_KEYS = {
    # Panneau financier (sous-phase 5a).
    "finance.revenue",
    "finance.expenses",
    "finance.margin",
    "finance.cash",
    "finance.budget",
    "finance.invoices_outstanding",
    "finance.top_clients",
    "finance.top_suppliers",
    # Mocks « simple » des autres modules.
    "web.visits",
    "social.followers",
    "projects.tasks_done",
}


async def _seed_org(session: AsyncSession, *, name: str, email: str) -> uuid.UUID:
    """Organisation + admin, tenant posé sur la session (RLS autorise l'écriture)."""
    organization_id, user_id = await seed_organization_with_admin(session, name=name, email=email)
    await set_tenant(session, user_id=user_id, organization_id=organization_id)
    return organization_id


async def _count_snapshots(
    session_factory: async_sessionmaker[AsyncSession], organization_id: uuid.UUID
) -> int:
    """Compte les snapshots de l'organisation (le tenant courant est posé d'abord)."""
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        result = await session.execute(text("SELECT count(*) FROM metric_snapshots"))
        return int(result.scalar_one())


async def test_sync_ecrit_les_quatre_modules(
    db_session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    organization_id = await _seed_org(db_session, name="Acme 4b", email="quatre@example.com")
    written = await sync_organization(db_session, organization_id)
    await db_session.commit()

    assert written > 0  # 4 séries × ~365 jours
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        result = await session.execute(text("SELECT DISTINCT metric_key FROM metric_snapshots"))
        assert set(result.scalars()) == EXPECTED_KEYS


async def test_resync_est_idempotent(
    db_session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    organization_id = await _seed_org(db_session, name="Acme re", email="resync@example.com")
    await sync_organization(db_session, organization_id)
    await db_session.commit()
    first_count = await _count_snapshots(session_factory, organization_id)

    await set_tenant(db_session, organization_id=organization_id)
    await sync_organization(db_session, organization_id)
    await db_session.commit()

    assert await _count_snapshots(session_factory, organization_id) == first_count


async def test_seed_deterministe_pour_l_organisation() -> None:
    organization_id = uuid.uuid4()
    assert seed_for_organization(organization_id) == seed_for_organization(organization_id)


async def test_isolation_entre_deux_organisations(
    db_session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    org_a = await _seed_org(db_session, name="Acme A", email="iso-a@example.com")
    await sync_organization(db_session, org_a)
    await db_session.commit()
    count_a = await _count_snapshots(session_factory, org_a)
    assert count_a > 0

    # Une seconde organisation : le worker change de tenant puis synchronise.
    org_b = await _seed_org(db_session, name="Acme B", email="iso-b@example.com")
    await sync_organization(db_session, org_b)
    await db_session.commit()
    count_b = await _count_snapshots(session_factory, org_b)

    assert count_b > 0
    assert await _count_snapshots(session_factory, org_a) == count_a  # A intacte


async def test_lecture_filtree_par_tenant_et_cle(
    db_session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    organization_id = await _seed_org(db_session, name="Acme lect", email="lect@example.com")
    await sync_organization(db_session, organization_id)
    await db_session.commit()

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        revenue = await metric_snapshots_repository.get_series(
            session, organization_id, "finance.revenue"
        )
        assert revenue
        assert all(snapshot.metric_key == "finance.revenue" for snapshot in revenue)
        assert all(snapshot.period == "P1D" for snapshot in revenue)

        # Fenêtre d'une journée : exactement un point.
        single_day = await metric_snapshots_repository.get_series(
            session,
            organization_id,
            "finance.revenue",
            start=revenue[0].captured_at,
            end=revenue[0].captured_at,
        )
        assert len(single_day) == 1


@pytest.mark.asyncio
async def test_read_sans_tenant_ne_renvoie_rien(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """RLS réelle : sans organisation posée, aucune ligne n'est visible."""
    async with session_factory() as session:
        result = await session.execute(text("SELECT count(*) FROM metric_snapshots"))
        assert int(result.scalar_one()) == 0
