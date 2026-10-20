"""Tests des objectifs et budgets (phase 6a-iii).

Couvre : création et lecture avec progression calculée, statuts `achieved`,
`on_track`, `off_track` et `unknown`, agrégation selon le type de métrique,
permissions par module (`view` lit mais n'écrit pas, `edit` écrit), restriction
de la liste aux modules visibles, mise à jour, suppression, journal d'audit,
isolation par organisation (RLS) et validation des entrées.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import API_PREFIX
from app.core.tenancy import set_tenant
from app.repositories import metric_snapshots as metric_snapshots_repository
from app.schemas.metrics import MetricSnapshotIn
from tests.helpers import audit_actions, csrf_headers, invite_and_accept, login, register_admin

PERIOD_DAYS = 5


def _goals_url(organization_id: uuid.UUID) -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/goals"


async def _seed(
    db_session: AsyncSession,
    organization_id: uuid.UUID,
    metric_key: str,
    unit: str,
    values: list[float],
) -> None:
    """Range une série quotidienne récente : dernier point ~12 h avant maintenant.

    Le décalage de 12 h garde chaque point loin des frontières de fenêtre : la
    fenêtre courante (5 derniers jours) et la précédente ne se chevauchent pas.
    """
    now = datetime.now(UTC)
    await set_tenant(db_session, organization_id=organization_id)
    snapshots = [
        MetricSnapshotIn(
            metric_key=metric_key,
            unit=unit,
            period="P1D",
            value=value,
            captured_at=now - timedelta(days=len(values) - 1 - index, hours=12),
        )
        for index, value in enumerate(values)
    ]
    await metric_snapshots_repository.upsert_many(db_session, organization_id, snapshots)
    await db_session.commit()


async def _create_goal(
    client: httpx.AsyncClient, organization_id: uuid.UUID, **overrides: object
) -> httpx.Response:
    payload: dict[str, object] = {
        "metric_key": "finance.revenue",
        "target_value": 30,
        "period_days": PERIOD_DAYS,
        "direction": "at_least",
    }
    payload.update(overrides)
    return await client.post(
        _goals_url(organization_id), json=payload, headers=csrf_headers(client)
    )


@pytest.mark.asyncio
async def test_creation_et_lecture_avec_progression(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(
        db_session, organization_id, "finance.revenue", "EUR", [float(i) for i in range(1, 11)]
    )

    created = await _create_goal(client, organization_id, target_value=30)

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["metric_key"] == "finance.revenue"
    assert body["direction"] == "at_least"
    assert body["period_days"] == PERIOD_DAYS
    # Fenêtre courante = 6+7+8+9+10 = 40 ; la cible 30 est dépassée.
    assert body["progress"]["current_value"] == 40.0
    assert body["progress"]["status"] == "achieved"
    assert body["progress"]["progress_percent"] == pytest.approx(133.33)
    assert body["progress"]["unit"] == "EUR"

    listed = await client.get(_goals_url(organization_id))
    assert listed.status_code == 200, listed.text
    assert [goal["metric_key"] for goal in listed.json()] == ["finance.revenue"]


@pytest.mark.asyncio
async def test_derive_quand_la_metrique_baisse(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(
        db_session, organization_id, "finance.revenue", "EUR", [float(i) for i in range(10, 0, -1)]
    )

    created = await _create_goal(client, organization_id, target_value=100)

    progress = created.json()["progress"]
    # Courante = 15 (1+2+3+4+5), précédente = 40 (10+9+8+7+6) : la métrique baisse.
    assert progress["current_value"] == 15.0
    assert progress["previous_value"] == 40.0
    assert progress["status"] == "off_track"
    assert progress["progress_percent"] == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_on_track_quand_la_metrique_progresse(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(
        db_session, organization_id, "finance.revenue", "EUR", [float(i) for i in range(1, 11)]
    )

    created = await _create_goal(client, organization_id, target_value=100)

    progress = created.json()["progress"]
    assert progress["current_value"] == 40.0
    assert progress["previous_value"] == 15.0
    assert progress["status"] == "on_track"
    assert progress["progress_percent"] == pytest.approx(40.0)


@pytest.mark.asyncio
async def test_budget_depasse_est_en_derive(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(
        db_session, organization_id, "finance.revenue", "EUR", [float(i) for i in range(1, 11)]
    )

    created = await _create_goal(client, organization_id, direction="at_most", target_value=30)

    progress = created.json()["progress"]
    # Un budget (`at_most`) de 30 est dépassé par 40, et la dépense augmente.
    assert progress["status"] == "off_track"
    assert progress["current_value"] == 40.0


@pytest.mark.asyncio
async def test_budget_respecte_est_atteint(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(
        db_session, organization_id, "finance.revenue", "EUR", [float(i) for i in range(1, 11)]
    )

    created = await _create_goal(client, organization_id, direction="at_most", target_value=100)

    assert created.json()["progress"]["status"] == "achieved"


@pytest.mark.asyncio
async def test_niveau_utilise_la_derniere_valeur(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    """`finance.cash` est un niveau : la dernière valeur de la fenêtre fait foi."""
    organization_id = await register_admin(client)
    await _seed(
        db_session, organization_id, "finance.cash", "EUR", [float(i) for i in range(1, 11)]
    )

    created = await _create_goal(
        client, organization_id, metric_key="finance.cash", target_value=10
    )

    progress = created.json()["progress"]
    assert progress["current_value"] == 10.0
    assert progress["previous_value"] == 5.0
    assert progress["status"] == "achieved"


@pytest.mark.asyncio
async def test_objectif_sans_donnee_est_inconnu(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    created = await _create_goal(client, organization_id, target_value=100)

    progress = created.json()["progress"]
    assert progress == {
        "current_value": None,
        "previous_value": None,
        "progress_percent": None,
        "status": "unknown",
        "unit": None,
    }


@pytest.mark.asyncio
async def test_membre_view_lit_mais_ne_cree_pas(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _create_goal(client, organization_id)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="lecteur@example.com",
        modules={"finance": "view"},
    )

    assert (await client.get(_goals_url(organization_id))).status_code == 200
    assert (await _create_goal(client, organization_id)).status_code == 403


@pytest.mark.asyncio
async def test_membre_edit_cree_sur_son_module(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="gestion@example.com",
        modules={"finance": "edit"},
    )

    assert (await _create_goal(client, organization_id)).status_code == 201
    # Le module web n'a pas été accordé : la cible web est refusée.
    denied = await _create_goal(client, organization_id, metric_key="web.visitors")
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_liste_restreinte_aux_modules_visibles(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await register_admin(client)
    await _create_goal(client, organization_id, metric_key="finance.revenue")
    await _create_goal(client, organization_id, metric_key="web.visitors")
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="finance@example.com",
        modules={"finance": "view"},
    )

    visible = await client.get(_goals_url(organization_id))
    assert [goal["metric_key"] for goal in visible.json()] == ["finance.revenue"]

    # Un second membre sans aucun module ne voit rien (jamais 403).
    await login(client, "admin@example.com")
    await invite_and_accept(
        app, client, organization_id=organization_id, email="sans@example.com", modules={}
    )
    empty = await client.get(_goals_url(organization_id))
    assert empty.status_code == 200
    assert empty.json() == []


@pytest.mark.asyncio
async def test_mise_a_jour_puis_suppression_et_audit(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    created = await _create_goal(client, organization_id, target_value=30)
    goal_id = created.json()["id"]

    updated = await client.patch(
        f"{_goals_url(organization_id)}/{goal_id}",
        json={"target_value": 10},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["target_value"] == 10

    deleted = await client.delete(
        f"{_goals_url(organization_id)}/{goal_id}", headers=csrf_headers(client)
    )
    assert deleted.status_code == 204
    assert (await client.get(_goals_url(organization_id))).json() == []

    actions = await audit_actions(session_factory, organization_id)
    assert "goal.created" in actions
    assert "goal.updated" in actions
    assert "goal.deleted" in actions


@pytest.mark.asyncio
async def test_objectif_inconnu_recoit_404(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    missing = uuid.uuid4()

    patched = await client.patch(
        f"{_goals_url(organization_id)}/{missing}",
        json={"target_value": 1},
        headers=csrf_headers(client),
    )
    deleted = await client.delete(
        f"{_goals_url(organization_id)}/{missing}", headers=csrf_headers(client)
    )

    assert patched.status_code == 404
    assert deleted.status_code == 404


@pytest.mark.asyncio
async def test_autre_organisation_recoit_403(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client, email="proprio@example.com")
    await register_admin(client, email="intrus@example.com")

    assert (await client.get(_goals_url(organization_id))).status_code == 403
    assert (await _create_goal(client, organization_id)).status_code == 403


@pytest.mark.asyncio
async def test_validation_des_entrees(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    assert (
        await _create_goal(client, organization_id, metric_key="pas-une-cle")
    ).status_code == 422
    assert (await _create_goal(client, organization_id, period_days=0)).status_code == 422
    assert (await _create_goal(client, organization_id, period_days=400)).status_code == 422


@pytest.mark.asyncio
async def test_isolation_rls_entre_organisations(
    client: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    organization_a = await register_admin(client, email="a@example.com")
    organization_b = await register_admin(client, email="b@example.com")

    insert = (
        "INSERT INTO goals (organization_id, metric_key, direction, target_value, period_days)"
        " VALUES (:organization_id, 'finance.revenue', 'at_least', 100, 30)"
    )
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_a)
        await session.execute(text(insert), {"organization_id": str(organization_a)})
        await session.commit()

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_b)
        count = await session.execute(text("SELECT count(*) FROM goals"))
        assert count.scalar_one() == 0

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_a)
        count = await session.execute(text("SELECT count(*) FROM goals"))
        assert count.scalar_one() == 1
