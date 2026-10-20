"""Tests des règles d'alerte configurables (phase 6c-iii).

Couvre : CRUD (création, liste filtrée par module visible, modification, suppression),
permission `edit` sur le module de la métrique, évaluation par le worker (seuil
franchi → notification `alert.threshold`, seuil non franchi → rien, métrique sans
donnée → rien), déduplication des non-lues, destinataires (admins + membres ayant
`edit`), isolation RLS entre organisations.
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
from app.services import alert_rules as alert_rules_service
from app.workers import sync as sync_worker
from tests.helpers import csrf_headers, invite_and_accept, login, register_admin

PERIOD_DAYS = 5


def _rules_url(organization_id: uuid.UUID) -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/alert-rules"


async def _seed(
    db_session: AsyncSession,
    organization_id: uuid.UUID,
    metric_key: str,
    unit: str,
    values: list[float],
) -> None:
    """Série quotidienne récente (12 h de décalage) dans la fenêtre courante."""
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


async def _create_rule(
    client: httpx.AsyncClient, organization_id: uuid.UUID, **overrides: object
) -> uuid.UUID:
    payload: dict[str, object] = {
        "metric_key": "finance.revenue",
        "comparison": "above",
        "threshold": 100,
        "period_days": PERIOD_DAYS,
    }
    payload.update(overrides)
    response = await client.post(
        _rules_url(organization_id), json=payload, headers=csrf_headers(client)
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def _evaluate(
    session_factory: async_sessionmaker[AsyncSession], organization_id: uuid.UUID
) -> None:
    """Déclenche l'évaluation des règles comme le ferait le worker de synchro."""
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        await alert_rules_service.evaluate_alert_rules(session, organization_id)
        await session.commit()


async def _unread_actions(
    session_factory: async_sessionmaker[AsyncSession], organization_id: uuid.UUID
) -> list[str]:
    """Kinds des notifications non lues de l'organisation (RLS : tenant posé)."""
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        result = await session.execute(
            text("SELECT kind FROM notifications WHERE read_at IS NULL ORDER BY kind")
        )
        return [row[0] for row in result.all()]


@pytest.mark.asyncio
async def test_crud_regle_d_alerte(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    rule_id = await _create_rule(
        client,
        organization_id,
        label="CA plancher",
        comparison="below",
        threshold=10,
    )

    listing = await client.get(_rules_url(organization_id))
    assert listing.status_code == 200, listing.text
    assert len(listing.json()) == 1
    assert listing.json()[0]["label"] == "CA plancher"
    assert listing.json()[0]["comparison"] == "below"

    updated = await client.patch(
        _rules_url(organization_id) + f"/{rule_id}",
        json={"enabled": False, "threshold": 20},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["enabled"] is False
    assert updated.json()["threshold"] == 20

    deleted = await client.delete(
        _rules_url(organization_id) + f"/{rule_id}", headers=csrf_headers(client)
    )
    assert deleted.status_code == 204, deleted.text
    assert (await client.get(_rules_url(organization_id))).json() == []


@pytest.mark.asyncio
async def test_creation_exige_edit_sur_le_module(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="lecteur@example.com",
        modules={"finance": "view"},
    )

    # Le lecteur (view) ne peut pas créer de règle sur finance.
    response = await client.post(
        _rules_url(organization_id),
        json={"metric_key": "finance.revenue", "comparison": "above", "threshold": 1},
        headers=csrf_headers(client),
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_liste_filtree_par_module_visible(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    await _create_rule(client, organization_id, metric_key="finance.revenue")
    await _create_rule(client, organization_id, metric_key="web.visitors")

    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="web@example.com",
        modules={"web": "view"},
    )

    # Le membre ne voit que la règle du module auquel il a accès.
    listing = await client.get(_rules_url(organization_id))
    assert listing.status_code == 200, listing.text
    assert [item["metric_key"] for item in listing.json()] == ["web.visitors"]


@pytest.mark.asyncio
async def test_seuil_franchi_genere_une_notification(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.invoices_outstanding", "EUR", [500.0, 500.0])
    await _create_rule(
        client,
        organization_id,
        metric_key="finance.invoices_outstanding",
        comparison="above",
        threshold=100,
    )

    await _evaluate(session_factory, organization_id)

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        result = await session.execute(text("SELECT kind, link, params FROM notifications"))
        rows = result.all()
    assert len(rows) == 1
    kind, link, params = rows[0]
    assert kind == "alert.threshold"
    assert link == "/finance"
    assert params["metric_key"] == "finance.invoices_outstanding"
    assert params["comparison"] == "above"


@pytest.mark.asyncio
async def test_seuil_non_franchi_ne_genere_rien(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [10.0, 10.0])
    await _create_rule(
        client, organization_id, metric_key="finance.revenue", comparison="above", threshold=100
    )

    await _evaluate(session_factory, organization_id)

    assert await _unread_actions(session_factory, organization_id) == []


@pytest.mark.asyncio
async def test_metrique_sans_donnee_ne_genere_rien(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _create_rule(client, organization_id, threshold=1)

    await _evaluate(session_factory, organization_id)

    assert await _unread_actions(session_factory, organization_id) == []


@pytest.mark.asyncio
async def test_regle_desactivee_non_evaluee(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [500.0, 500.0])
    await _create_rule(client, organization_id, threshold=100, enabled=False)

    await _evaluate(session_factory, organization_id)

    assert await _unread_actions(session_factory, organization_id) == []


@pytest.mark.asyncio
async def test_deduplication_sur_les_passages_successifs(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [500.0, 500.0])
    await _create_rule(client, organization_id, threshold=100)

    await _evaluate(session_factory, organization_id)
    await _evaluate(session_factory, organization_id)

    assert await _unread_actions(session_factory, organization_id) == ["alert.threshold"]


@pytest.mark.asyncio
async def test_membre_avec_edit_notifie_mais_view_non(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="editeur@example.com",
        modules={"finance": "edit"},
    )
    await login(client, "admin@example.com")
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="lecteur@example.com",
        modules={"finance": "view"},
    )
    await login(client, "admin@example.com")
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [500.0, 500.0])
    await _create_rule(client, organization_id, threshold=100)

    await _evaluate(session_factory, organization_id)

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        result = await session.execute(
            text(
                "SELECT u.email FROM notifications n"
                " JOIN users u ON u.id = n.user_id ORDER BY u.email"
            )
        )
        emails = [row[0] for row in result.all()]
    assert emails == ["admin@example.com", "editeur@example.com"]


@pytest.mark.asyncio
async def test_autre_organisation_recoit_403(app: FastAPI, client: httpx.AsyncClient) -> None:
    await register_admin(client)

    forbidden = await client.get(_rules_url(uuid.uuid4()))
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_isolation_rls_entre_organisations(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_org = await register_admin(client)
    await _seed(db_session, first_org, "finance.revenue", "EUR", [500.0, 500.0])
    await _create_rule(client, first_org, threshold=100)
    await _evaluate(session_factory, first_org)

    second_org = await register_admin(client, email="deuxieme@example.com")
    await _evaluate(session_factory, second_org)

    async with session_factory() as session:
        # Sans tenant posé, la RLS ne renvoie aucune ligne (défense en profondeur).
        result = await session.execute(text("SELECT count(*) FROM alert_rules"))
        assert result.scalar_one() == 0
        await set_tenant(session, organization_id=second_org)
        result = await session.execute(text("SELECT count(*) FROM alert_rules"))
        assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_le_worker_de_synchro_evalue_les_regles(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La synchro est le moment où les seuils sont vérifiés (câblage du worker)."""
    organization_id = await register_admin(client)
    synced: list[uuid.UUID] = []
    evaluated: list[uuid.UUID] = []

    async def fake_sync(session: AsyncSession, org_id: uuid.UUID) -> int:
        synced.append(org_id)
        return 0

    async def fake_evaluate(
        session: AsyncSession, org_id: uuid.UUID, *, push_sender: object = None
    ) -> None:
        evaluated.append(org_id)

    monkeypatch.setattr(sync_worker, "sync_organization", fake_sync)
    monkeypatch.setattr(alert_rules_service, "evaluate_alert_rules", fake_evaluate)

    await sync_worker.sync_all_organizations(session_factory)

    assert synced == [organization_id]
    assert evaluated == [organization_id]
