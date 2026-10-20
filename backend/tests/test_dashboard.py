"""Tests de la mise en page du tableau de bord (phase 6b-ii-a).

Couvre : catalogue de widgets filtré par permission (KPI par module visible,
activité réservée aux admins), mise en page par défaut quand rien n'est
enregistré, enregistrement (PUT) validé et audité, remise à zéro (DELETE),
mise en page propre à chaque utilisateur, refus des widgets inconnus (422) ou
interdits (403), bornes de la grille (x + w ≤ 12), filtrage à la lecture quand
un droit a disparu, isolation par organisation (RLS) et validation des entrées.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import API_PREFIX
from app.core.tenancy import set_tenant
from tests.helpers import audit_actions, csrf_headers, invite_and_accept, login, register_admin

# Les huit clés KPI du Pouls, dans l'ordre du catalogue.
KPI_KEYS = [
    "finance.revenue",
    "finance.margin",
    "web.visitors",
    "web.conversions",
    "social.followers",
    "social.engagement_rate",
    "projects.open_tasks",
    "projects.avg_progress",
]
KPI_WIDGETS = [f"kpi.{key}" for key in KPI_KEYS]
BASE_WIDGETS = ["health", *KPI_WIDGETS, "goals", "activity"]


def _url(organization_id: uuid.UUID) -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/dashboard"


def _placement(
    widget_id: str, *, x: int = 0, y: int = 0, w: int = 4, h: int = 2
) -> dict[str, object]:
    return {"widget_id": widget_id, "x": x, "y": y, "w": w, "h": h}


async def _save(
    client: httpx.AsyncClient, organization_id: uuid.UUID, widgets: list[dict[str, object]]
) -> httpx.Response:
    return await client.put(
        _url(organization_id), json={"widgets": widgets}, headers=csrf_headers(client)
    )


@pytest.mark.asyncio
async def test_mise_en_page_par_defaut_pour_un_admin(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await register_admin(client)

    response = await client.get(_url(organization_id))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["is_default"] is True
    assert [widget["widget_id"] for widget in payload["available_widgets"]] == BASE_WIDGETS
    assert {widget["widget_id"] for widget in payload["layout"]} == set(BASE_WIDGETS)
    health = next(w for w in payload["layout"] if w["widget_id"] == "health")
    assert (health["x"], health["y"], health["w"], health["h"]) == (0, 0, 12, 2)


@pytest.mark.asyncio
async def test_catalogue_filtre_par_module_visible(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="finance@example.com",
        modules={"finance": "view"},
    )

    payload = (await client.get(_url(organization_id))).json()

    widget_ids = [widget["widget_id"] for widget in payload["available_widgets"]]
    # Seuls les KPI de la finance + santé + objectifs ; l'activité reste admin.
    assert widget_ids == ["health", "kpi.finance.revenue", "kpi.finance.margin", "goals"]
    assert {widget["widget_id"] for widget in payload["layout"]} == set(widget_ids)


@pytest.mark.asyncio
async def test_catalogue_decrit_le_genre_et_la_metrique(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await register_admin(client)

    widgets = {
        w["widget_id"]: w
        for w in (await client.get(_url(organization_id))).json()["available_widgets"]
    }

    assert widgets["health"]["kind"] == "health"
    assert widgets["goals"]["kind"] == "goals"
    assert widgets["activity"]["kind"] == "activity"
    kpi = widgets["kpi.finance.revenue"]
    assert kpi["kind"] == "kpi"
    assert kpi["module"] == "finance"
    assert kpi["metric_key"] == "finance.revenue"


@pytest.mark.asyncio
async def test_enregistrement_puis_lecture_et_audit(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    widgets = [_placement("health", w=12), _placement("goals", x=0, y=2, w=6, h=6)]

    saved = await _save(client, organization_id, widgets)

    assert saved.status_code == 200, saved.text
    payload = saved.json()
    assert payload["is_default"] is False
    assert [w["widget_id"] for w in payload["layout"]] == ["health", "goals"]
    assert payload["layout"][1]["h"] == 6

    reread = (await client.get(_url(organization_id))).json()
    assert reread["is_default"] is False
    assert [w["widget_id"] for w in reread["layout"]] == ["health", "goals"]

    assert "dashboard.layout.updated" in await audit_actions(session_factory, organization_id)


@pytest.mark.asyncio
async def test_remise_a_zero_restaure_le_defaut(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _save(client, organization_id, [_placement("health", w=12)])

    deleted = await client.delete(_url(organization_id), headers=csrf_headers(client))

    assert deleted.status_code == 204
    payload = (await client.get(_url(organization_id))).json()
    assert payload["is_default"] is True
    assert {w["widget_id"] for w in payload["layout"]} == set(BASE_WIDGETS)
    assert "dashboard.layout.reset" in await audit_actions(session_factory, organization_id)


@pytest.mark.asyncio
async def test_mise_en_page_propre_a_chaque_utilisateur(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await register_admin(client)
    await _save(client, organization_id, [_placement("health", w=12)])

    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="membre@example.com",
        modules={"finance": "view"},
    )
    member_default = (await client.get(_url(organization_id))).json()
    assert member_default["is_default"] is True  # le membre n'a rien enregistré
    await _save(client, organization_id, [_placement("goals", w=6, h=6)])

    await login(client, "admin@example.com")
    admin_layout = (await client.get(_url(organization_id))).json()
    assert [w["widget_id"] for w in admin_layout["layout"]] == ["health"]

    await login(client, "membre@example.com")
    member_layout = (await client.get(_url(organization_id))).json()
    assert [w["widget_id"] for w in member_layout["layout"]] == ["goals"]


@pytest.mark.asyncio
async def test_widget_inconnu_refuse(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    response = await _save(client, organization_id, [_placement("inexistant")])

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_doublon_de_widget_refuse(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    response = await _save(
        client, organization_id, [_placement("health", w=6), _placement("health", x=6, w=6)]
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_widget_hors_grille_refuse(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    # x + w = 13 déborde des 12 colonnes.
    assert (
        await _save(client, organization_id, [_placement("health", x=6, w=7)])
    ).status_code == 422
    assert (await _save(client, organization_id, [_placement("health", x=-1)])).status_code == 422
    assert (await _save(client, organization_id, [_placement("health", w=0)])).status_code == 422
    assert (await _save(client, organization_id, [_placement("health", h=0)])).status_code == 422
    assert (await _save(client, organization_id, [_placement("health", h=99)])).status_code == 422


@pytest.mark.asyncio
async def test_membre_ne_peut_pas_ajouter_l_activite(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="membre@example.com",
        modules={"finance": "view"},
    )

    response = await _save(client, organization_id, [_placement("activity")])

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_membre_ne_peut_pas_ajouter_un_module_invisible(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="membre@example.com",
        modules={"finance": "view"},
    )

    response = await _save(client, organization_id, [_placement("kpi.web.visitors")])

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_lecture_filtre_un_widget_devenu_interdit(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Un widget enregistré puis interdit disparaît à la lecture (défense en profondeur)."""
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="membre@example.com",
        modules={"finance": "view"},
    )
    # Insertion directe (le service refuse d'écrire un widget interdit) : simule un
    # droit retiré après l'enregistrement.
    widgets = '[{"widget_id": "activity", "x": 0, "y": 0, "w": 6, "h": 6}]'
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        await session.execute(
            text(
                "INSERT INTO dashboard_layouts (organization_id, user_id, widgets)"
                " SELECT :organization_id, m.user_id, CAST(:widgets AS jsonb)"
                " FROM memberships m WHERE m.organization_id = :organization_id"
                " AND m.role = 'member'"
            ),
            {"organization_id": str(organization_id), "widgets": widgets},
        )
        await session.commit()

    payload = (await client.get(_url(organization_id))).json()

    assert payload["is_default"] is False
    assert payload["layout"] == []


@pytest.mark.asyncio
async def test_autre_organisation_recoit_403(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client, email="proprio@example.com")
    await register_admin(client, email="intrus@example.com")

    assert (await client.get(_url(organization_id))).status_code == 403
    assert (await _save(client, organization_id, [_placement("health", w=12)])).status_code == 403
    assert (
        await client.delete(_url(organization_id), headers=csrf_headers(client))
    ).status_code == 403


@pytest.mark.asyncio
async def test_isolation_rls_entre_organisations(
    client: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    organization_a = await register_admin(client, email="a@example.com")
    organization_b = await register_admin(client, email="b@example.com")

    widgets = '[{"widget_id": "health", "x": 0, "y": 0, "w": 12, "h": 2}]'
    insert = (
        "INSERT INTO dashboard_layouts (organization_id, user_id, widgets)"
        " SELECT :organization_id, m.user_id, CAST(:widgets AS jsonb)"
        " FROM memberships m WHERE m.organization_id = :organization_id"
    )
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_a)
        await session.execute(
            text(insert),
            {"organization_id": str(organization_a), "widgets": widgets},
        )
        await session.commit()

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_b)
        count = await session.execute(text("SELECT count(*) FROM dashboard_layouts"))
        assert count.scalar_one() == 0

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_a)
        count = await session.execute(text("SELECT count(*) FROM dashboard_layouts"))
        assert count.scalar_one() == 1
