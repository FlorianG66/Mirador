"""Isolation multi-tenant : Row-Level Security PostgreSQL (AGENTS.md §5)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import ORGANIZATION_TENANT_GUC, USER_TENANT_GUC, set_tenant
from app.models.membership import Membership
from tests.conftest import current_setting, seed_organization_with_admin


async def test_set_tenant_exposes_both_settings_to_postgresql(db_session: AsyncSession) -> None:
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()

    await set_tenant(db_session, user_id=user_id, organization_id=organization_id)

    assert await current_setting(db_session, USER_TENANT_GUC) == str(user_id)
    assert await current_setting(db_session, ORGANIZATION_TENANT_GUC) == str(organization_id)


async def test_set_tenant_without_context_clears_the_previous_one(db_session: AsyncSession) -> None:
    """Une requête sans utilisateur ni organisation ne doit jamais hériter du tenant précédent."""
    await set_tenant(db_session, user_id=uuid.uuid4(), organization_id=uuid.uuid4())

    await set_tenant(db_session)

    assert await current_setting(db_session, USER_TENANT_GUC) in (None, "")
    assert await current_setting(db_session, ORGANIZATION_TENANT_GUC) in (None, "")


async def test_tenant_context_dies_with_its_transaction(db_session: AsyncSession) -> None:
    """Paramètre local (is_local) : la transaction suivante repart de zéro, sans fuite."""
    await set_tenant(db_session, user_id=uuid.uuid4(), organization_id=uuid.uuid4())

    await db_session.commit()

    assert await current_setting(db_session, USER_TENANT_GUC) in (None, "")
    assert await current_setting(db_session, ORGANIZATION_TENANT_GUC) in (None, "")


async def test_rows_are_invisible_without_a_tenant_context(db_session: AsyncSession) -> None:
    organization_id, _user_id = await seed_organization_with_admin(
        db_session, name="Alpha", email="alpha@example.com"
    )
    await set_tenant(db_session)

    result = await db_session.execute(
        select(Membership).where(Membership.organization_id == organization_id)
    )

    assert result.scalars().all() == []


async def test_a_tenant_only_sees_its_own_memberships(db_session: AsyncSession) -> None:
    alpha_id, _ = await seed_organization_with_admin(
        db_session, name="Alpha", email="a@example.com"
    )
    beta_id, _ = await seed_organization_with_admin(db_session, name="Beta", email="b@example.com")

    await set_tenant(db_session, organization_id=alpha_id)

    alpha = await db_session.execute(
        select(Membership).where(Membership.organization_id == alpha_id)
    )
    beta = await db_session.execute(select(Membership).where(Membership.organization_id == beta_id))
    assert len(alpha.scalars().all()) == 1
    assert beta.scalars().all() == []


async def test_user_context_is_enough_to_read_his_memberships(db_session: AsyncSession) -> None:
    """Connexion : l'utilisateur est connu avant l'organisation (SPEC §2)."""
    _alpha_id, alpha_user_id = await seed_organization_with_admin(
        db_session, name="Alpha", email="a@example.com"
    )
    _beta_id, _beta_user_id = await seed_organization_with_admin(
        db_session, name="Beta", email="b@example.com"
    )

    await set_tenant(db_session, user_id=alpha_user_id)

    result = await db_session.execute(select(Membership))
    assert [membership.user_id for membership in result.scalars().all()] == [alpha_user_id]
