"""Repositories de la phase 2 : organisations, utilisateurs, memberships."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import set_tenant
from app.models.enums import Role
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User
from app.repositories import memberships as memberships_repository
from app.repositories import organizations as organizations_repository
from app.repositories import users as users_repository
from tests.conftest import seed_organization_with_admin


async def test_create_and_get_organization(db_session: AsyncSession) -> None:
    organization = await organizations_repository.create_organization(
        db_session, name="Alpha", siren="123456789"
    )
    await db_session.commit()

    stored = await organizations_repository.get_organization(db_session, organization.id)

    assert stored is not None
    assert stored.name == "Alpha"
    assert stored.siren == "123456789"


async def test_get_unknown_organization_returns_none(db_session: AsyncSession) -> None:
    assert await organizations_repository.get_organization(db_session, uuid.uuid4()) is None


async def test_create_user_and_find_him_by_email(db_session: AsyncSession) -> None:
    user = await users_repository.create_user(
        db_session, email="admin@example.com", password_hash="hachage-factice"
    )
    await db_session.commit()

    stored = await users_repository.get_user_by_email(db_session, "admin@example.com")

    assert stored is not None
    assert stored.id == user.id
    assert stored.password_hash == "hachage-factice"


async def test_get_user_by_unknown_email_returns_none(db_session: AsyncSession) -> None:
    assert await users_repository.get_user_by_email(db_session, "absent@example.com") is None


async def test_two_users_cannot_share_the_same_email(db_session: AsyncSession) -> None:
    await users_repository.create_user(db_session, email="dup@example.com", password_hash="un")
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await users_repository.create_user(
            db_session, email="dup@example.com", password_hash="deux"
        )
    await db_session.rollback()


async def test_create_membership_and_list_members(db_session: AsyncSession) -> None:
    organization_id, _admin_id = await seed_organization_with_admin(
        db_session, name="Alpha", email="membership-admin@example.com"
    )
    member = await users_repository.create_user(
        db_session, email="membre@example.com", password_hash="hachage-factice"
    )
    await memberships_repository.create_membership(
        db_session,
        organization_id=organization_id,
        user_id=member.id,
        role=Role.MEMBER,
    )

    members = await memberships_repository.list_members(db_session, organization_id=organization_id)

    assert len(members) == 2
    assert {membership.role for membership in members} == {Role.ADMIN, Role.MEMBER}


async def test_duplicate_membership_is_rejected(db_session: AsyncSession) -> None:
    organization_id, user_id = await seed_organization_with_admin(
        db_session, name="Alpha", email="duplicate-admin@example.com"
    )

    with pytest.raises(IntegrityError):
        await memberships_repository.create_membership(
            db_session,
            organization_id=organization_id,
            user_id=user_id,
            role=Role.MEMBER,
        )
    await db_session.rollback()


async def test_members_of_another_organization_are_invisible(db_session: AsyncSession) -> None:
    """Défense en profondeur : le filtre explicite ne suffit pas, la RLS tranche."""
    alpha_id, _ = await seed_organization_with_admin(
        db_session, name="Alpha", email="a@example.com"
    )
    beta_id, _ = await seed_organization_with_admin(db_session, name="Beta", email="b@example.com")

    await set_tenant(db_session, organization_id=beta_id)
    visible_from_beta = await memberships_repository.list_members(
        db_session, organization_id=alpha_id
    )
    assert visible_from_beta == []

    await set_tenant(db_session, organization_id=alpha_id)
    visible_from_alpha = await memberships_repository.list_members(
        db_session, organization_id=alpha_id
    )
    assert len(visible_from_alpha) == 1


async def test_list_memberships_for_user_returns_only_his(db_session: AsyncSession) -> None:
    _alpha_id, alpha_user_id = await seed_organization_with_admin(
        db_session, name="Alpha", email="a@example.com"
    )
    _beta_id, beta_user_id = await seed_organization_with_admin(
        db_session, name="Beta", email="b@example.com"
    )
    await set_tenant(db_session, user_id=alpha_user_id)

    memberships = await memberships_repository.list_memberships_for_user(
        db_session, user_id=alpha_user_id
    )

    assert [membership.user_id for membership in memberships] == [alpha_user_id]
    assert [membership.user_id for membership in memberships] != [beta_user_id]


async def test_membership_points_to_existing_rows(db_session: AsyncSession) -> None:
    """Le schéma lie les tables : un membership ne peut pas flotter sans organisation."""
    organization = await organizations_repository.create_organization(db_session, name="Alpha")
    user = await users_repository.create_user(
        db_session, email="orphan@example.com", password_hash="hachage-factice"
    )
    await set_tenant(db_session, user_id=user.id, organization_id=organization.id)
    membership = await memberships_repository.create_membership(
        db_session,
        organization_id=organization.id,
        user_id=user.id,
        role=Role.ADMIN,
    )
    await db_session.flush()

    stored_membership = await db_session.get(Membership, membership.id)
    stored_user = await db_session.get(User, user.id)
    stored_organization = await db_session.get(Organization, organization.id)
    assert stored_membership is not None
    assert stored_user is not None
    assert stored_organization is not None
    assert stored_membership.organization_id == stored_organization.id
    assert stored_membership.user_id == stored_user.id


async def test_list_members_on_unknown_organization_is_empty(db_session: AsyncSession) -> None:
    assert await memberships_repository.list_members(db_session, organization_id=uuid.uuid4()) == []


async def test_select_users_table_is_not_tenant_scoped(db_session: AsyncSession) -> None:
    """`users` est une table d'identité globale : pas de RLS (voir DECISIONS)."""
    await users_repository.create_user(db_session, email="global@example.com", password_hash="x")
    await set_tenant(db_session, organization_id=uuid.uuid4())

    result = await db_session.execute(select(User).where(User.email == "global@example.com"))

    assert result.scalar_one_or_none() is not None
