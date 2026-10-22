"""Mode démo (phase 7) : scénarios, sessions isolées, liens, purge, registres.

Les tests couvrent les trois exigences de la phase : aucune fuite entre une
organisation de démonstration et un vrai tenant, expiration des liens, remise à
zéro automatique (purge des organisations démo arrivées à échéance).
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import API_PREFIX
from app.core.tenancy import set_tenant
from app.workers.sync import sync_all_organizations
from tests.conftest import register_client
from tests.helpers import csrf_headers, install_legal_registry

DEMO_PREFIX = f"{API_PREFIX}/demo"
DEMO_EMAIL_DOMAIN = "example.com"


async def start_demo(client: httpx.AsyncClient, *, sector: str = "restaurant") -> dict[str, object]:
    """Ouvre une session de démonstration et retourne le corps de la réponse."""
    response = await client.post(f"{DEMO_PREFIX}/sessions", json={"sector": sector})
    assert response.status_code == 201, response.text
    return response.json()


async def create_demo_link(
    client: httpx.AsyncClient, organization_id: uuid.UUID, *, sector: str = "agency"
) -> httpx.Response:
    """Génère un lien de démonstration en tant qu'admin de l'organisation."""
    return await client.post(
        f"{API_PREFIX}/organizations/{organization_id}/demo-links",
        json={"sector": sector},
        headers=csrf_headers(client),
    )


async def test_demo_scenarios_are_public(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{DEMO_PREFIX}/scenarios")

    assert response.status_code == 200
    assert {scenario["key"] for scenario in response.json()} == {
        "restaurant",
        "agency",
        "ecommerce",
    }


async def test_demo_session_provisions_a_fictional_isolated_tenant(
    client: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    body = await start_demo(client)
    organization = body["organization"]
    organization_id = uuid.UUID(str(organization["id"]))

    assert organization["is_demo"] is True
    assert body["sector"] == "restaurant"

    me = await client.get(f"{API_PREFIX}/auth/me")
    assert me.status_code == 200
    membership = me.json()["memberships"][0]
    assert membership["is_demo"] is True
    assert membership["organization_name"] == organization["name"]
    assert membership["demo_sector"] == "restaurant"

    legal = await client.get(f"{API_PREFIX}/organizations/{organization_id}/legal")
    assert legal.status_code == 200
    profile = legal.json()
    assert profile["siren"] == "000000000"
    assert "fictive" in profile["raison_sociale"].lower()
    assert "fictive" in profile["adresse_siege"].lower()
    assert profile["sources"]["raison_sociale"]["source"] == "demo"

    # Les MockConnectors ont alimenté l'organisation : la démo n'est pas vide.
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        count = await session.execute(text("SELECT count(*) FROM metric_snapshots"))
        assert count.scalar_one() > 0


async def test_demo_session_never_calls_the_legal_registry(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    registry = install_legal_registry(app)

    body = await start_demo(client)
    organization_id = uuid.UUID(str(body["organization"]["id"]))

    assert registry.calls == []
    refresh = await client.post(
        f"{API_PREFIX}/organizations/{organization_id}/legal/refresh",
        headers=csrf_headers(client),
    )
    assert refresh.status_code == 403
    assert registry.calls == []


async def test_demo_cannot_read_a_real_tenant(
    client: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    registered = await register_client(client)
    assert registered.status_code == 201
    real_organization_id = uuid.UUID(registered.json()["organization"]["id"])

    # Marqueur unique : s'il apparaît côté démo, la RLS a fui.
    async with session_factory() as session:
        await set_tenant(session, organization_id=real_organization_id)
        await session.execute(
            text(
                "INSERT INTO metric_snapshots"
                " (organization_id, metric_key, unit, period, value, captured_at)"
                " VALUES (:organization_id, 'finance.demo_isolation_sentinel',"
                " 'EUR', 'P1D', 1, now())"
            ),
            {"organization_id": real_organization_id},
        )
        await session.commit()

    demo = await start_demo(client)
    demo_organization_id = uuid.UUID(str(demo["organization"]["id"]))

    forbidden = await client.get(f"{API_PREFIX}/organizations/{real_organization_id}/legal")
    assert forbidden.status_code == 403

    async with session_factory() as session:
        await set_tenant(session, organization_id=demo_organization_id)
        leaked = await session.execute(
            text(
                "SELECT count(*) FROM metric_snapshots"
                " WHERE metric_key = 'finance.demo_isolation_sentinel'"
            )
        )
        assert leaked.scalar_one() == 0


async def test_expired_demo_link_is_rejected(
    client: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    registered = await register_client(client)
    organization_id = uuid.UUID(registered.json()["organization"]["id"])
    link = await create_demo_link(client, organization_id)
    assert link.status_code == 201, link.text
    token = link.json()["token"]

    async with session_factory() as session:
        await session.execute(
            text("UPDATE demo_links SET expires_at = now() - interval '1 minute'")
        )
        await session.commit()

    client.cookies.clear()
    expired = await client.post(f"{DEMO_PREFIX}/links/{token}")
    assert expired.status_code == 410


async def test_unknown_demo_link_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(f"{DEMO_PREFIX}/links/jeton-inconnu")
    assert response.status_code == 410


async def test_demo_link_opens_the_linked_sector(client: httpx.AsyncClient) -> None:
    registered = await register_client(client)
    organization_id = uuid.UUID(registered.json()["organization"]["id"])
    link = await create_demo_link(client, organization_id, sector="ecommerce")
    assert link.status_code == 201, link.text
    body = link.json()
    assert body["sector"] == "ecommerce"
    assert body["path"] == f"/demo/{body['token']}"

    # Le prospect n'a pas de compte : les cookies de l'admin sont écartés.
    client.cookies.clear()
    opened = await client.post(f"{DEMO_PREFIX}/links/{body['token']}")

    assert opened.status_code == 201, opened.text
    assert opened.json()["sector"] == "ecommerce"
    me = await client.get(f"{API_PREFIX}/auth/me")
    assert me.status_code == 200
    assert me.json()["memberships"][0]["organization_name"].startswith("Boutique")


async def test_a_demo_organization_cannot_generate_more_demo_links(
    client: httpx.AsyncClient,
) -> None:
    demo = await start_demo(client)
    organization_id = uuid.UUID(str(demo["organization"]["id"]))

    response = await create_demo_link(client, organization_id)

    assert response.status_code == 403


async def test_expired_demo_is_purged_with_its_data(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registered = await register_client(client)
    real_organization_id = uuid.UUID(registered.json()["organization"]["id"])
    demo = await start_demo(client)
    demo_organization_id = uuid.UUID(str(demo["organization"]["id"]))

    async with session_factory() as session:
        await session.execute(
            text(
                "UPDATE organizations SET demo_expires_at = now() - interval '1 minute'"
                " WHERE is_demo"
            )
        )
        await session.commit()

    await sync_all_organizations(app.state.session_factory)

    async with session_factory() as session:
        remaining_orgs = await session.execute(
            text("SELECT count(*) FROM organizations WHERE id = :organization_id"),
            {"organization_id": demo_organization_id},
        )
        assert remaining_orgs.scalar_one() == 0
        real_orgs = await session.execute(
            text("SELECT count(*) FROM organizations WHERE id = :organization_id"),
            {"organization_id": real_organization_id},
        )
        assert real_orgs.scalar_one() == 1
        demo_users = await session.execute(
            text("SELECT count(*) FROM users WHERE email LIKE :pattern"),
            {"pattern": f"demo+%@{DEMO_EMAIL_DOMAIN}"},
        )
        assert demo_users.scalar_one() == 0
        demo_metrics = await session.execute(
            text("SELECT count(*) FROM metric_snapshots WHERE organization_id = :organization_id"),
            {"organization_id": demo_organization_id},
        )
        assert demo_metrics.scalar_one() == 0

    # La session du visiteur tombe avec le compte : la démo est bien remise à zéro.
    me = await client.get(f"{API_PREFIX}/auth/me")
    assert me.status_code == 401


async def test_demo_creation_is_rate_limited(client: httpx.AsyncClient) -> None:
    for _ in range(5):
        response = await client.post(f"{DEMO_PREFIX}/sessions", json={"sector": "restaurant"})
        assert response.status_code == 201, response.text

    blocked = await client.post(f"{DEMO_PREFIX}/sessions", json={"sector": "restaurant"})

    assert blocked.status_code == 429
    assert "retry-after" in {header.lower() for header in blocked.headers}


async def test_unknown_sector_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(f"{DEMO_PREFIX}/sessions", json={"sector": "banque"})
    assert response.status_code == 422
