"""Invitations : création par l'admin, révocation, acceptation (SPEC §2, phase 2d)."""

from __future__ import annotations

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import API_PREFIX
from app.core.rate_limit import INVITE_RATE_LIMIT
from app.core.security import generate_token, hash_token
from app.core.tenancy import set_tenant
from tests.conftest import register_client
from tests.helpers import (
    EMPTY_MODULES,
    FakeEmailSender,
    audit_actions,
    csrf_headers,
    extract_invitation_link,
    invite,
    invite_and_accept,
    login,
    modules_with,
    register_admin,
)

MEMBER_EMAIL = "membre@example.com"


async def test_admin_can_invite_a_collaborator_with_modules(
    client: httpx.AsyncClient,
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    sender = FakeEmailSender()
    app.state.email_sender = sender

    response = await invite(
        client, organization_id, email=MEMBER_EMAIL, modules={"finance": "view"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == MEMBER_EMAIL
    assert body["role"] == "member"
    assert body["modules"] == modules_with(finance="view")
    assert body["expires_at"]
    to, _subject, content = sender.sent[0]
    assert to == MEMBER_EMAIL
    token, organization = extract_invitation_link(content)
    assert organization == str(organization_id)
    async with session_factory() as session:
        # RLS : sans tenant posé, la table invitations est vide pour la session.
        await set_tenant(session, organization_id=organization_id)
        digest = (
            await session.execute(
                text("SELECT token_hash FROM invitations WHERE organization_id = :organization"),
                {"organization": str(organization_id)},
            )
        ).scalar_one()
    # Seul le hachage du jeton est stocké : l'e-mail seul ne permet pas d'usurper.
    assert digest == hash_token(token)
    assert digest != token
    assert await audit_actions(session_factory, organization_id) == ["invitation.created"]


async def test_invite_requires_a_membership_in_the_organization(
    client: httpx.AsyncClient,
) -> None:
    organization_id = await register_admin(client)
    await register_client(client, email="intrus@example.com")

    response = await invite(client, organization_id, email="cible@example.com")

    assert response.status_code == 403
    assert response.json()["detail"] == "Vous n'avez pas accès à cette organisation."


async def test_invite_is_admin_only(client: httpx.AsyncClient, app: FastAPI) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(app, client, organization_id=organization_id, email=MEMBER_EMAIL)

    response = await invite(client, organization_id, email="autre@example.com")

    assert response.status_code == 403
    assert response.json()["detail"] == "Réservé aux administrateurs."


async def test_invite_rejects_an_unknown_module_or_level(
    client: httpx.AsyncClient,
) -> None:
    organization_id = await register_admin(client)

    unknown_module = await invite(
        client, organization_id, email="cible@example.com", modules={"inconnu": "view"}
    )
    unknown_level = await invite(
        client, organization_id, email="cible@example.com", modules={"finance": "superuser"}
    )

    assert unknown_module.status_code == 422
    assert unknown_level.status_code == 422


async def test_invite_conflicts_with_an_existing_member(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(app, client, organization_id=organization_id, email=MEMBER_EMAIL)
    client.cookies.clear()
    assert (await login(client, "admin@example.com")).status_code == 200

    response = await invite(client, organization_id, email=MEMBER_EMAIL)

    assert response.status_code == 409
    assert response.json()["detail"] == "Cet e-mail est déjà membre de l'organisation."


async def test_invite_conflicts_with_a_pending_invitation(client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    first = await invite(client, organization_id, email=MEMBER_EMAIL)

    second = await invite(client, organization_id, email=MEMBER_EMAIL)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Une invitation est déjà en attente pour cet e-mail."


async def test_invite_is_rate_limited(client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    for index in range(INVITE_RATE_LIMIT):
        attempt = await invite(client, organization_id, email=f"invite-{index}@example.com")
        assert attempt.status_code == 201

    blocked = await invite(client, organization_id, email="dernier@example.com")

    assert blocked.status_code == 429


async def test_admin_can_list_and_revoke_an_invitation(
    client: httpx.AsyncClient,
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    sender = FakeEmailSender()
    app.state.email_sender = sender
    created = await invite(client, organization_id, email=MEMBER_EMAIL, modules={"finance": "view"})
    invitation_id = created.json()["id"]

    listing = await client.get(f"{API_PREFIX}/organizations/{organization_id}/invitations")
    assert listing.status_code == 200
    assert [row["email"] for row in listing.json()] == [MEMBER_EMAIL]

    revoked = await client.delete(
        f"{API_PREFIX}/organizations/{organization_id}/invitations/{invitation_id}",
        headers=csrf_headers(client),
    )
    assert revoked.status_code == 204

    empty = await client.get(f"{API_PREFIX}/organizations/{organization_id}/invitations")
    assert empty.json() == []
    assert await audit_actions(session_factory, organization_id) == [
        "invitation.created",
        "invitation.revoked",
    ]

    # Le jeton révoqué ne vaut plus rien, même s'il n'a pas expiré.
    token, organization = extract_invitation_link(sender.sent[0][2])
    client.cookies.clear()
    await register_client(client, email=MEMBER_EMAIL)
    accept = await client.post(
        f"{API_PREFIX}/auth/invitations/accept",
        json={"token": token, "organization_id": organization},
        headers=csrf_headers(client),
    )
    assert accept.status_code == 401


async def test_accept_creates_the_membership_and_module_permissions(
    client: httpx.AsyncClient,
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)

    accepted = await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email=MEMBER_EMAIL,
        modules={"finance": "view", "legal": "edit"},
    )

    assert accepted.json() == {
        "organization_id": str(organization_id),
        "role": "member",
        "modules": modules_with(finance="view", legal="edit"),
    }
    team = await client.get(f"{API_PREFIX}/organizations/{organization_id}/members")
    assert team.status_code == 200
    assert {row["email"] for row in team.json()} == {"admin@example.com", MEMBER_EMAIL}
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        rows = await session.execute(
            text("SELECT module, level FROM module_permissions ORDER BY module")
        )
        levels = [(row[0], row[1]) for row in rows.all()]
    assert levels == [("finance", "view"), ("legal", "edit")]
    assert await audit_actions(session_factory, organization_id) == [
        "invitation.created",
        "invitation.accepted",
    ]


async def test_accept_requires_authentication(client: httpx.AsyncClient, app: FastAPI) -> None:
    organization_id = await register_admin(client)
    sender = FakeEmailSender()
    app.state.email_sender = sender
    await invite(client, organization_id, email=MEMBER_EMAIL)
    token, organization = extract_invitation_link(sender.sent[0][2])
    client.cookies.clear()

    response = await client.post(
        f"{API_PREFIX}/auth/invitations/accept",
        json={"token": token, "organization_id": organization},
    )

    assert response.status_code == 401


async def test_accept_rejects_another_recipient(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    organization_id = await register_admin(client)
    sender = FakeEmailSender()
    app.state.email_sender = sender
    await invite(client, organization_id, email="autre@example.com")
    token, organization = extract_invitation_link(sender.sent[0][2])

    # L'admin est connecté mais l'invitation est adressée à quelqu'un d'autre.
    response = await client.post(
        f"{API_PREFIX}/auth/invitations/accept",
        json={"token": token, "organization_id": organization},
        headers=csrf_headers(client),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cette invitation n'est pas destinée à cet e-mail."


async def test_accept_rejects_an_expired_invitation(
    client: httpx.AsyncClient,
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    sender = FakeEmailSender()
    app.state.email_sender = sender
    await invite(client, organization_id, email=MEMBER_EMAIL)
    token, organization = extract_invitation_link(sender.sent[0][2])
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        await session.execute(
            text("UPDATE invitations SET expires_at = now() - interval '1 minute'")
        )
        await session.commit()
    client.cookies.clear()
    await register_client(client, email=MEMBER_EMAIL)

    response = await client.post(
        f"{API_PREFIX}/auth/invitations/accept",
        json={"token": token, "organization_id": organization},
        headers=csrf_headers(client),
    )

    assert response.status_code == 401


async def test_accept_cannot_be_replayed(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    organization_id = await register_admin(client)
    accepted = await invite_and_accept(
        app, client, organization_id=organization_id, email=MEMBER_EMAIL
    )
    assert accepted.status_code == 201
    sender: FakeEmailSender = app.state.email_sender
    token, organization = extract_invitation_link(sender.sent[-1][2])

    replay = await client.post(
        f"{API_PREFIX}/auth/invitations/accept",
        json={"token": token, "organization_id": organization},
        headers=csrf_headers(client),
    )

    assert replay.status_code == 401


async def test_accept_conflicts_with_an_existing_membership(
    client: httpx.AsyncClient,
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(app, client, organization_id=organization_id, email=MEMBER_EMAIL)
    # Le service refuse d'inviter un membre existant : la seconde invitation est
    # donc émise directement en base, pour éprouver le garde-fou de l'acceptation.
    token = generate_token()
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        await session.execute(
            text(
                "INSERT INTO invitations (organization_id, invited_by_id, email, role,"
                " module_permissions, token_hash, expires_at)"
                " SELECT :organization, users.id, :email, 'member', '[]'::jsonb,"
                " :token_hash, now() + interval '7 days'"
                " FROM users WHERE users.email = 'admin@example.com'"
            ),
            {
                "organization": str(organization_id),
                "email": MEMBER_EMAIL,
                "token_hash": hash_token(token),
            },
        )
        await session.commit()
    client.cookies.clear()
    assert (await login(client, MEMBER_EMAIL)).status_code == 200

    response = await client.post(
        f"{API_PREFIX}/auth/invitations/accept",
        json={"token": token, "organization_id": str(organization_id)},
        headers=csrf_headers(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Vous êtes déjà membre de cette organisation."


async def test_modules_default_to_none_for_an_invitation_without_choices(
    client: httpx.AsyncClient,
) -> None:
    organization_id = await register_admin(client)

    response = await invite(client, organization_id, email=MEMBER_EMAIL)

    assert response.status_code == 201
    assert response.json()["modules"] == EMPTY_MODULES
