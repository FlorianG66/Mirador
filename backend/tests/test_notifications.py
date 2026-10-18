"""Tests des notifications in-app (phase 6c-ii).

Couvre : génération depuis les événements existants (objectif atteint, objectif en
dérive, écart sur la fiche légale), destinataires (admins + membres ayant `edit`
sur le module de l'objectif ; admins seuls pour le légal), déduplication, liste
personnelle avec compteur de non-lus, marquage lu / tout lu, isolation par
utilisateur et par organisation (RLS).

Les règles d'alerte configurables (`alert_rules`) viennent en 6c-iii : ici seules
les notifications déclenchées par des événements déjà produits sont testées.
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
from app.services import notifications as notifications_service
from app.workers import sync as sync_worker
from tests.helpers import (
    SIREN_VALIDE,
    csrf_headers,
    install_legal_registry,
    invite_and_accept,
    login,
    register_admin,
    register_client,
    sample_company,
)

PERIOD_DAYS = 5


async def _register_admin_with_siren(
    client: httpx.AsyncClient, *, email: str = "admin@example.com"
) -> uuid.UUID:
    """Inscription d'un admin dont l'organisation porte déjà un SIREN (fiche légale)."""
    response = await register_client(client, email=email, siren=SIREN_VALIDE)
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["organization"]["id"])


def _notifications_url(organization_id: uuid.UUID) -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/notifications"


async def _seed(
    db_session: AsyncSession,
    organization_id: uuid.UUID,
    metric_key: str,
    unit: str,
    values: list[float],
    *,
    days_ago: list[int] | None = None,
) -> None:
    """Série quotidienne récente (12 h de décalage).

    Sans `days_ago`, les points sont collés aux derniers jours (fenêtre courante).
    Avec, chaque valeur est placée explicitement (utile pour peupler la fenêtre
    précédente et déclencher une dérive).
    """
    now = datetime.now(UTC)
    offsets = (
        days_ago
        if days_ago is not None
        else [len(values) - 1 - index for index in range(len(values))]
    )
    await set_tenant(db_session, organization_id=organization_id)
    snapshots = [
        MetricSnapshotIn(
            metric_key=metric_key,
            unit=unit,
            period="P1D",
            value=value,
            captured_at=now - timedelta(days=offset, hours=12),
        )
        for value, offset in zip(values, offsets, strict=True)
    ]
    await metric_snapshots_repository.upsert_many(db_session, organization_id, snapshots)
    await db_session.commit()


async def _create_goal(
    client: httpx.AsyncClient, organization_id: uuid.UUID, **overrides: object
) -> uuid.UUID:
    payload: dict[str, object] = {
        "metric_key": "finance.revenue",
        "target_value": 30,
        "period_days": PERIOD_DAYS,
        "direction": "at_least",
    }
    payload.update(overrides)
    response = await client.post(
        f"{API_PREFIX}/organizations/{organization_id}/goals",
        json=payload,
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def _evaluate(
    session_factory: async_sessionmaker[AsyncSession], organization_id: uuid.UUID
) -> None:
    """Déclenche l'évaluation des objectifs comme le ferait le worker de synchro."""
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        await notifications_service.evaluate_goal_notifications(session, organization_id)
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
async def test_objectif_atteint_genere_une_notification(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [50.0, 50.0, 50.0])
    await _create_goal(client, organization_id, target_value=100)

    await _evaluate(session_factory, organization_id)

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        result = await session.execute(
            text("SELECT user_id, kind, link, read_at FROM notifications")
        )
        rows = result.all()
    assert len(rows) == 1
    user_id, kind, link, read_at = rows[0]
    assert kind == "goal.achieved"
    assert link is not None and link.startswith("/finance")
    assert read_at is None


@pytest.mark.asyncio
async def test_derive_genere_une_notification_off_track(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    # Fenêtre précédente (jours -9/-8) forte, fenêtre courante (jours -2/-1/0)
    # faible : l'agrégat baisse (dérive) tout en restant sous la cible (30).
    await _seed(
        db_session,
        organization_id,
        "finance.revenue",
        "EUR",
        [400.0, 400.0, 5.0, 5.0, 5.0],
        days_ago=[9, 8, 2, 1, 0],
    )
    await _create_goal(client, organization_id, target_value=30)

    await _evaluate(session_factory, organization_id)

    assert await _unread_actions(session_factory, organization_id) == ["goal.off_track"]


@pytest.mark.asyncio
async def test_objectif_sans_donnee_ne_genere_rien(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _create_goal(client, organization_id)

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
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [50.0, 50.0, 50.0])
    await _create_goal(client, organization_id, target_value=100)

    await _evaluate(session_factory, organization_id)
    await _evaluate(session_factory, organization_id)

    assert await _unread_actions(session_factory, organization_id) == ["goal.achieved"]


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
    # L'acceptation connecte l'invité : on repasse admin avant la seconde invitation.
    await login(client, "admin@example.com")
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="lecteur@example.com",
        modules={"finance": "view"},
    )
    # Reconnecte l'admin pour créer l'objectif (il a `edit` partout).
    await login(client, "admin@example.com")
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [50.0, 50.0, 50.0])
    goal_id = await _create_goal(client, organization_id, target_value=100)

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
    # L'admin et l'éditeur sont notifiés ; le lecteur (view) ne l'est pas.
    assert emails == ["admin@example.com", "editeur@example.com"]
    assert goal_id is not None


@pytest.mark.asyncio
async def test_liste_personnelle_et_compteur_de_non_lus(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [50.0, 50.0, 50.0])
    await _create_goal(client, organization_id, target_value=100)
    await _evaluate(session_factory, organization_id)

    response = await client.get(_notifications_url(organization_id))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["unread_count"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["kind"] == "goal.achieved"
    assert item["read_at"] is None
    assert item["params"]["metric_key"] == "finance.revenue"
    assert item["created_at"] is not None


@pytest.mark.asyncio
async def test_marquage_lu_et_tout_lu(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [50.0, 50.0, 50.0])
    await _create_goal(client, organization_id, target_value=100)
    await _create_goal(client, organization_id, target_value=100, metric_key="web.visitors")
    await _seed(db_session, organization_id, "web.visitors", "count", [50.0, 50.0, 50.0])
    await _evaluate(session_factory, organization_id)

    listing = await client.get(_notifications_url(organization_id))
    assert listing.json()["unread_count"] == 2
    first_id = listing.json()["items"][0]["id"]

    marked = await client.post(
        _notifications_url(organization_id) + f"/{first_id}/read", headers=csrf_headers(client)
    )
    assert marked.status_code == 204, marked.text

    after_one = await client.get(_notifications_url(organization_id))
    assert after_one.json()["unread_count"] == 1

    marked_all = await client.post(
        _notifications_url(organization_id) + "/read-all", headers=csrf_headers(client)
    )
    assert marked_all.status_code == 204, marked_all.text

    final = await client.get(_notifications_url(organization_id))
    assert final.json()["unread_count"] == 0
    assert all(item["read_at"] is not None for item in final.json()["items"])


@pytest.mark.asyncio
async def test_marquage_lu_d_autrui_recoit_404(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR", [50.0, 50.0, 50.0])
    await _create_goal(client, organization_id, target_value=100)
    await _evaluate(session_factory, organization_id)
    listing = await client.get(_notifications_url(organization_id))
    notification_id = listing.json()["items"][0]["id"]

    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="autre@example.com",
        modules={"finance": "view"},
    )

    # L'autre membre ne voit pas la notification dans sa liste…
    other_listing = await client.get(_notifications_url(organization_id))
    assert other_listing.json()["items"] == []
    # …et ne peut pas la marquer comme lue.
    response = await client.post(
        _notifications_url(organization_id) + f"/{notification_id}/read",
        headers=csrf_headers(client),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_divergence_legale_notifie_les_admins(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await _register_admin_with_siren(client)
    install_legal_registry(app, companies=[sample_company(adresse="99 rue Autre")])
    # Saisie manuelle divergente : le registre dira autre chose → `diverged`.
    update = await client.put(
        f"{API_PREFIX}/organizations/{organization_id}/legal",
        json={"adresse_siege": "12 rue Originale"},
        headers=csrf_headers(client),
    )
    assert update.status_code == 200, update.text
    refresh = await client.post(
        f"{API_PREFIX}/organizations/{organization_id}/legal/refresh",
        headers=csrf_headers(client),
    )
    assert refresh.status_code == 200, refresh.text

    actions = await _unread_actions(session_factory, organization_id)
    assert actions == ["legal.diverged"]


@pytest.mark.asyncio
async def test_divergence_legale_ne_notifie_pas_les_membres(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await _register_admin_with_siren(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="membre@example.com",
        modules={"legal": "edit"},
    )
    install_legal_registry(app, companies=[sample_company(adresse="99 rue Autre")])
    await login(client, "admin@example.com")
    update = await client.put(
        f"{API_PREFIX}/organizations/{organization_id}/legal",
        json={"adresse_siege": "12 rue Originale"},
        headers=csrf_headers(client),
    )
    assert update.status_code == 200, update.text
    refresh = await client.post(
        f"{API_PREFIX}/organizations/{organization_id}/legal/refresh",
        headers=csrf_headers(client),
    )
    assert refresh.status_code == 200, refresh.text

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        result = await session.execute(
            text("SELECT u.email FROM notifications n JOIN users u ON u.id = n.user_id")
        )
        emails = [row[0] for row in result.all()]
    assert emails == ["admin@example.com"]


@pytest.mark.asyncio
async def test_autre_organisation_recoit_403(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    await register_admin(client)

    forbidden = await client.get(f"{API_PREFIX}/organizations/{uuid.uuid4()}/notifications")
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_isolation_rls_entre_organisations(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_org = await register_admin(client)
    await _seed(db_session, first_org, "finance.revenue", "EUR", [50.0, 50.0, 50.0])
    await _create_goal(client, first_org, target_value=100)
    await _evaluate(session_factory, first_org)

    second_org = await register_admin(client, email="deuxieme@example.com")
    await _evaluate(session_factory, second_org)

    async with session_factory() as session:
        # Sans tenant posé, la RLS ne renvoie aucune ligne (défense en profondeur).
        result = await session.execute(text("SELECT count(*) FROM notifications"))
        assert result.scalar_one() == 0
        await set_tenant(session, organization_id=second_org)
        result = await session.execute(text("SELECT count(*) FROM notifications"))
        assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_le_worker_de_synchro_evalue_les_objectifs(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La synchro est le moment où les cibles sont vérifiées (câblage du worker)."""
    organization_id = await register_admin(client)
    synced: list[uuid.UUID] = []
    evaluated: list[uuid.UUID] = []

    async def fake_sync(session: AsyncSession, org_id: uuid.UUID) -> int:
        synced.append(org_id)
        return 0

    async def fake_evaluate(session: AsyncSession, org_id: uuid.UUID) -> None:
        evaluated.append(org_id)

    monkeypatch.setattr(sync_worker, "sync_organization", fake_sync)
    monkeypatch.setattr(notifications_service, "evaluate_goal_notifications", fake_evaluate)

    await sync_worker.sync_all_organizations(session_factory)

    assert synced == [organization_id]
    assert evaluated == [organization_id]
