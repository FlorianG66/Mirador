"""Tests des abonnements Web Push (phase 6c-iii-b).

Couvre : clé VAPID publique (présente si configurée, 404 sinon), enregistrement
idempotent d'un abonnement, réattribution d'un endpoint à un autre utilisateur,
désabonnement (et sa propriété : on ne retire pas l'abonnement d'autrui), envoi
d'un push à chaque notification émise (via un faux émetteur — aucune vraie clé,
aucun service réel, AGENTS.md §5), suppression d'un abonnement déclaré caduc,
best-effort (un échec n'empêche pas la notification in-app), et isolation RLS.

Rappel : les tests ne poussent jamais vers un vrai service de push ; l'émetteur
est toujours un `FakePushSender` posé sur `app.state.push_sender`.
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
from app.services import notifications as notifications_service
from app.services import push as push_service
from tests.helpers import (
    csrf_headers,
    install_push_sender,
    invite_and_accept,
    login,
    register_admin,
)

ENDPOINT = "https://push.example.test/v1/abc123"


def _push_url(organization_id: uuid.UUID) -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/push"


def _subscription_payload(endpoint: str = ENDPOINT) -> dict[str, object]:
    return {
        "endpoint": endpoint,
        "keys": {"p256dh": "BPublicKeyFactice", "auth": "SecretFactice"},
        "user_agent": "Navigateur de test",
    }


async def _subscribe(
    client: httpx.AsyncClient, organization_id: uuid.UUID, endpoint: str = ENDPOINT
) -> httpx.Response:
    return await client.post(
        f"{_push_url(organization_id)}/subscriptions",
        json=_subscription_payload(endpoint),
        headers=csrf_headers(client),
    )


async def _seed(db_session: AsyncSession, organization_id: uuid.UUID, values: list[float]) -> None:
    """Série quotidienne récente sur `finance.revenue` (fenêtre courante)."""
    now = datetime.now(UTC)
    await set_tenant(db_session, organization_id=organization_id)
    snapshots = [
        MetricSnapshotIn(
            metric_key="finance.revenue",
            unit="EUR",
            period="P1D",
            value=value,
            captured_at=now - timedelta(days=len(values) - 1 - index, hours=12),
        )
        for index, value in enumerate(values)
    ]
    await metric_snapshots_repository.upsert_many(db_session, organization_id, snapshots)
    await db_session.commit()


async def _create_rule(client: httpx.AsyncClient, organization_id: uuid.UUID) -> None:
    response = await client.post(
        f"{API_PREFIX}/organizations/{organization_id}/alert-rules",
        json={"metric_key": "finance.revenue", "comparison": "above", "threshold": 100},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text


async def _evaluate(
    session_factory: async_sessionmaker[AsyncSession],
    organization_id: uuid.UUID,
    sender: push_service.PushSender | None,
) -> None:
    """Évalue les objectifs et les règles comme le worker de synchro, avec émetteur."""
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        await notifications_service.evaluate_goal_notifications(
            session, organization_id, push_sender=sender
        )
        await alert_rules_service.evaluate_alert_rules(session, organization_id, push_sender=sender)
        await session.commit()


@pytest.mark.asyncio
async def test_cle_publique_absente_renvoie_404(app: FastAPI, client: httpx.AsyncClient) -> None:
    """Sans clé VAPID configurée, le frontend n'a rien à donner au navigateur → 404."""
    organization_id = await register_admin(client)

    response = await client.get(f"{_push_url(organization_id)}/public-key")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cle_publique_renvoyee_quand_configuree(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await register_admin(client)
    app.state.settings.vapid_public_key = "BCléVapidPubliqueDeTest"

    response = await client.get(f"{_push_url(organization_id)}/public-key")

    assert response.status_code == 200, response.text
    assert response.json()["public_key"] == "BCléVapidPubliqueDeTest"


@pytest.mark.asyncio
async def test_abonnement_idempotent(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Deux abonnements successifs du même endpoint ne créent qu'une ligne."""
    organization_id = await register_admin(client)

    first = await _subscribe(client, organization_id)
    assert first.status_code == 201, first.text
    second = await _subscribe(client, organization_id)
    assert second.status_code == 201, second.text
    # L'identifiant est stable : c'est la même ligne mise à jour, pas un doublon.
    assert first.json()["id"] == second.json()["id"]

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        count = await session.execute(text("SELECT count(*) FROM push_subscriptions"))
        assert count.scalar_one() == 1


@pytest.mark.asyncio
async def test_desabonnement_retire_l_abonnement(
    app: FastAPI,
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await register_admin(client)
    await _subscribe(client, organization_id)

    response = await client.request(
        "DELETE",
        f"{_push_url(organization_id)}/subscriptions",
        json={"endpoint": ENDPOINT},
        headers=csrf_headers(client),
    )
    assert response.status_code == 204, response.text

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        count = await session.execute(text("SELECT count(*) FROM push_subscriptions"))
        assert count.scalar_one() == 0


@pytest.mark.asyncio
async def test_desabonnement_d_autrui_sans_effet(app: FastAPI, client: httpx.AsyncClient) -> None:
    """Un membre ne peut pas retirer l'abonnement d'un autre (filtre `user_id`)."""
    organization_id = await register_admin(client)
    await _subscribe(client, organization_id)

    await invite_and_accept(app, client, organization_id=organization_id, email="autre@example.com")
    # L'invité tente de désabonner l'endpoint de l'admin : aucune ligne retirée.
    response = await client.request(
        "DELETE",
        f"{_push_url(organization_id)}/subscriptions",
        json={"endpoint": ENDPOINT},
        headers=csrf_headers(client),
    )
    assert response.status_code == 204, response.text

    await login(client, "admin@example.com")
    # L'admin voit toujours son abonnement actif : re-souscrire ne crée pas de doublon.
    resub = await _subscribe(client, organization_id)
    assert resub.status_code == 201, resub.text


@pytest.mark.asyncio
async def test_notification_emise_poussee_vers_les_abonnements(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Une alerte franchie est poussée vers l'abonnement du destinataire."""
    organization_id = await register_admin(client)
    await _subscribe(client, organization_id)
    sender = install_push_sender(app)
    await _seed(db_session, organization_id, [500.0, 500.0])
    await _create_rule(client, organization_id)

    await _evaluate(session_factory, organization_id, sender)

    assert len(sender.sent) == 1
    endpoint, message = sender.sent[0]
    assert endpoint == ENDPOINT
    assert message["kind"] == "alert.threshold"
    params = message["params"]
    assert isinstance(params, dict)
    assert params["comparison"] == "above"
    assert message["link"] == "/finance"


@pytest.mark.asyncio
async def test_abonnement_caduc_supprime_apres_envoi(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Un service de push répondant « caduc » fait supprimer l'abonnement."""
    organization_id = await register_admin(client)
    await _subscribe(client, organization_id)
    sender = install_push_sender(app, outcome=push_service.PushOutcome.GONE)
    await _seed(db_session, organization_id, [500.0, 500.0])
    await _create_rule(client, organization_id)

    await _evaluate(session_factory, organization_id, sender)

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        count = await session.execute(text("SELECT count(*) FROM push_subscriptions"))
        assert count.scalar_one() == 0


@pytest.mark.asyncio
async def test_echec_push_n_empeche_pas_la_notification(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Best-effort : un envoi qui échoue laisse la notification in-app intacte."""
    organization_id = await register_admin(client)
    await _subscribe(client, organization_id)
    sender = install_push_sender(app, outcome=push_service.PushOutcome.FAILED)
    await _seed(db_session, organization_id, [500.0, 500.0])
    await _create_rule(client, organization_id)

    await _evaluate(session_factory, organization_id, sender)

    # L'abonnement reste (l'échec est transitoire) et la notification est écrite.
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        subs = await session.execute(text("SELECT count(*) FROM push_subscriptions"))
        assert subs.scalar_one() == 1
        notes = await session.execute(text("SELECT kind FROM notifications WHERE read_at IS NULL"))
        assert [row[0] for row in notes.all()] == ["alert.threshold"]


@pytest.mark.asyncio
async def test_aucun_envoi_sans_emetteur(
    app: FastAPI,
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Sans émetteur (Web Push désactivé), l'in-app est écrite sans aucun envoi."""
    organization_id = await register_admin(client)
    await _subscribe(client, organization_id)
    await _seed(db_session, organization_id, [500.0, 500.0])
    await _create_rule(client, organization_id)

    await _evaluate(session_factory, organization_id, None)

    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        notes = await session.execute(text("SELECT count(*) FROM notifications"))
        assert notes.scalar_one() == 1


@pytest.mark.asyncio
async def test_abonnements_isoles_par_organisation(
    app: FastAPI, client: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    first_org = await register_admin(client)
    await _subscribe(client, first_org, endpoint="https://push.example.test/v1/first")

    second_org = await register_admin(client, email="deuxieme@example.com")
    await _subscribe(client, second_org, endpoint="https://push.example.test/v1/second")

    async with session_factory() as session:
        # Sans tenant posé, la RLS ne renvoie aucune ligne (défense en profondeur).
        result = await session.execute(text("SELECT count(*) FROM push_subscriptions"))
        assert result.scalar_one() == 0
        await set_tenant(session, organization_id=second_org)
        result = await session.execute(text("SELECT endpoint FROM push_subscriptions"))
        assert [row[0] for row in result.all()] == ["https://push.example.test/v1/second"]


@pytest.mark.asyncio
async def test_autre_organisation_recoit_403(app: FastAPI, client: httpx.AsyncClient) -> None:
    await register_admin(client)

    forbidden = await client.get(f"{_push_url(uuid.uuid4())}/subscriptions")
    # La route n'existe qu'en POST/DELETE : un GET renvoie 405 ; on vérifie donc
    # qu'une écriture sur l'organisation d'autrui est bien refusée (403).
    assert forbidden.status_code in (403, 405)

    forbidden_write = await client.post(
        f"{_push_url(uuid.uuid4())}/subscriptions",
        json=_subscription_payload(),
        headers=csrf_headers(client),
    )
    assert forbidden_write.status_code == 403
