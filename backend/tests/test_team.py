"""Équipe : membres, permissions par module, révocation, journal d'audit (SPEC §2, phase 2d)."""

from __future__ import annotations

import uuid

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import API_PREFIX
from app.core.tenancy import set_tenant
from tests.conftest import register_client
from tests.helpers import (
    ADMIN_MODULES,
    audit_actions,
    csrf_headers,
    invite_and_accept,
    login,
    modules_with,
    register_admin,
)

MEMBER_EMAIL = "membre@example.com"


async def test_a_member_can_list_the_team_with_effective_permissions(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email=MEMBER_EMAIL,
        modules={"finance": "view"},
    )

    team = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")

    assert team.status_code == 200
    by_email = {row["email"]: row for row in team.json()}
    assert len(by_email) == 2
    assert by_email["admin@example.com"]["role"] == "admin"
    assert by_email["admin@example.com"]["modules"] == ADMIN_MODULES
    assert by_email[MEMBER_EMAIL]["role"] == "member"
    assert by_email[MEMBER_EMAIL]["modules"] == modules_with(finance="view")


async def test_the_team_is_forbidden_to_another_tenant(client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    await register_client(client, email="intrus@example.com")

    response = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")

    assert response.status_code == 403
    assert response.json()["detail"] == "Vous n'avez pas accès à cette organisation."


async def test_permissions_endpoint_reports_admin_and_member_levels(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    organization_id = await register_admin(client)

    mine = await client.get(f"{API_PREFIX}/organizations/{organization_id}/permissions")
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email=MEMBER_EMAIL,
        modules={"finance": "view"},
    )
    theirs = await client.get(f"{API_PREFIX}/organizations/{organization_id}/permissions")

    assert mine.status_code == theirs.status_code == 200
    assert mine.json() == {"role": "admin", "modules": ADMIN_MODULES}
    assert theirs.json() == {"role": "member", "modules": modules_with(finance="view")}


async def test_admin_can_update_a_member_permissions_and_is_audited(
    client: httpx.AsyncClient,
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email=MEMBER_EMAIL,
        modules={"finance": "view"},
    )
    team = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")
    member_id = next(row["user_id"] for row in team.json() if row["email"] == MEMBER_EMAIL)
    client.cookies.clear()
    assert (await login(client, "admin@example.com")).status_code == 200

    response = await client.patch(
        f"{API_PREFIX}/organizations/{organization_id}/members/{member_id}/permissions",
        json={"modules": {"finance": "edit", "web": "view"}},
        headers=csrf_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["modules"] == modules_with(finance="edit", web="view")
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        rows = await session.execute(
            text(
                "SELECT module, level FROM module_permissions mp"
                " JOIN memberships m ON m.id = mp.membership_id"
                " WHERE m.user_id = :user ORDER BY module"
            ),
            {"user": uuid.UUID(member_id)},
        )
        levels = [(row[0], row[1]) for row in rows.all()]
        payload = (
            await session.execute(
                text(
                    "SELECT payload FROM audit_logs WHERE action = 'membership.permissions.updated'"
                )
            )
        ).scalar_one()
    assert levels == [("finance", "edit"), ("web", "view")]
    assert payload["before"] == modules_with(finance="view")
    assert payload["after"] == modules_with(finance="edit", web="view")
    assert await audit_actions(session_factory, organization_id) == [
        "invitation.created",
        "invitation.accepted",
        "membership.permissions.updated",
    ]


async def test_update_permissions_is_admin_only(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(app, client, organization_id=organization_id, email=MEMBER_EMAIL)
    team = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")
    admin_id = next(row["user_id"] for row in team.json() if row["email"] == "admin@example.com")

    response = await client.patch(
        f"{API_PREFIX}/organizations/{organization_id}/members/{admin_id}/permissions",
        json={"modules": {"finance": "edit"}},
        headers=csrf_headers(client),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Réservé aux administrateurs."


async def test_update_permissions_rejects_an_unknown_module(
    client: httpx.AsyncClient,
) -> None:
    organization_id = await register_admin(client)
    team = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")
    admin_id = team.json()[0]["user_id"]

    response = await client.patch(
        f"{API_PREFIX}/organizations/{organization_id}/members/{admin_id}/permissions",
        json={"modules": {"inconnu": "view"}},
        headers=csrf_headers(client),
    )

    assert response.status_code == 422


async def test_update_permissions_of_a_non_member_is_404(
    client: httpx.AsyncClient,
) -> None:
    organization_id = await register_admin(client)

    response = await client.patch(
        f"{API_PREFIX}/organizations/{organization_id}/members/{uuid.uuid4()}/permissions",
        json={"modules": {"finance": "view"}},
        headers=csrf_headers(client),
    )

    assert response.status_code == 404


async def test_admin_can_revoke_a_member_and_loses_their_access(
    client: httpx.AsyncClient,
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email=MEMBER_EMAIL,
        modules={"finance": "view"},
    )
    team = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")
    member_id = next(row["user_id"] for row in team.json() if row["email"] == MEMBER_EMAIL)
    client.cookies.clear()
    assert (await login(client, "admin@example.com")).status_code == 200

    response = await client.delete(
        f"{API_PREFIX}/organizations/{organization_id}/members/{member_id}",
        headers=csrf_headers(client),
    )

    assert response.status_code == 204
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        remaining_members = (
            await session.execute(text("SELECT count(*) FROM memberships"))
        ).scalar_one()
        remaining_permissions = (
            await session.execute(text("SELECT count(*) FROM module_permissions"))
        ).scalar_one()
    assert remaining_members == 1
    assert remaining_permissions == 0  # suppression en cascade des permissions
    assert "membership.revoked" in await audit_actions(session_factory, organization_id)

    # Le compte existe toujours, mais son accès à l'organisation a disparu.
    client.cookies.clear()
    assert (await login(client, MEMBER_EMAIL)).status_code == 200
    lost = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")
    assert lost.status_code == 403


async def test_revoke_is_admin_only(client: httpx.AsyncClient, app: FastAPI) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(app, client, organization_id=organization_id, email=MEMBER_EMAIL)
    team = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")
    admin_id = next(row["user_id"] for row in team.json() if row["email"] == "admin@example.com")

    response = await client.delete(
        f"{API_PREFIX}/organizations/{organization_id}/members/{admin_id}",
        headers=csrf_headers(client),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Réservé aux administrateurs."


async def test_an_admin_cannot_revoke_themselves(client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    team = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")
    admin_id = team.json()[0]["user_id"]

    response = await client.delete(
        f"{API_PREFIX}/organizations/{organization_id}/members/{admin_id}",
        headers=csrf_headers(client),
    )

    # Seul admin de son organisation : il ne peut pas s'y couper lui-même.
    assert response.status_code == 400
    assert response.json()["detail"] == "Vous ne pouvez pas révoquer votre propre accès."


async def test_revoke_of_a_non_member_is_404(client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    response = await client.delete(
        f"{API_PREFIX}/organizations/{organization_id}/members/{uuid.uuid4()}",
        headers=csrf_headers(client),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Membre introuvable."


async def test_audit_logs_are_admin_only_and_readable(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(app, client, organization_id=organization_id, email=MEMBER_EMAIL)

    as_member = await client.get(f"{API_PREFIX}/organizations/{organization_id}/audit-logs")
    client.cookies.clear()
    assert (await login(client, "admin@example.com")).status_code == 200
    as_admin = await client.get(f"{API_PREFIX}/organizations/{organization_id}/audit-logs")

    assert as_member.status_code == 403
    assert as_member.json()["detail"] == "Réservé aux administrateurs."
    assert as_admin.status_code == 200
    actions = {row["action"] for row in as_admin.json()}
    assert {"invitation.created", "invitation.accepted"} <= actions
    assert as_admin.json()[0]["created_at"]
