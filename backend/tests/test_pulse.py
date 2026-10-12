"""Tests de l'endpoint du Pouls (phase 5f).

Couvre : KPI clés filtrés par module autorisé, valeur précédente pour la
tendance, santé d'exploitation (verte / en alerte / inconnue), fil d'activité
réservé aux admins, absence de donnée, et refus hors organisation. Les données
sont rangées en base (tenant posé) avant d'être lues via l'API (RLS réelle).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import API_PREFIX
from app.core.tenancy import set_tenant
from app.repositories import metric_snapshots as metric_snapshots_repository
from app.schemas.metrics import MetricSnapshotIn
from tests.helpers import invite, invite_and_accept, register_admin

# Les huit KPI clés attendus, unités fidèles aux connecteurs (SPEC §5.4).
_KPI_UNITS: dict[str, str] = {
    "finance.revenue": "EUR",
    "finance.margin": "EUR",
    "web.visitors": "visitors",
    "web.conversions": "conversions",
    "social.followers": "followers",
    "social.engagement_rate": "%",
    "projects.open_tasks": "tasks",
    "projects.avg_progress": "%",
}


def _pulse_url(organization_id: uuid.UUID) -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/pulse"


async def _seed_keys(
    db_session: AsyncSession, organization_id: uuid.UUID, keys: list[str], *, points: int = 2
) -> None:
    """Range deux points par clé (le plus récent d'abord) pour tester la tendance."""
    await set_tenant(db_session, organization_id=organization_id)
    now = datetime.now(UTC)
    snapshots = [
        MetricSnapshotIn(
            metric_key=key,
            unit=_KPI_UNITS.get(key, "unit"),
            period="P1D",
            value=100.0 + index + offset,
            captured_at=now - timedelta(days=offset),
        )
        for index, key in enumerate(keys)
        for offset in range(points)
    ]
    await metric_snapshots_repository.upsert_many(db_session, organization_id, snapshots)
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_voit_les_huit_kpi_et_une_sante_verte(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_keys(db_session, organization_id, list(_KPI_UNITS))

    response = await client.get(_pulse_url(organization_id))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [kpi["metric_key"] for kpi in payload["kpis"]] == list(_KPI_UNITS)
    assert payload["health"] == {
        "status": "good",
        "modules_with_data": 4,
        "modules_total": 4,
    }
    # La tendance dispose de la valeur précédente quand deux points existent.
    assert payload["kpis"][0]["previous_value"] is not None


@pytest.mark.asyncio
async def test_un_membre_ne_voit_que_les_kpi_de_ses_modules(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_keys(db_session, organization_id, list(_KPI_UNITS))
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="compta@example.com",
        modules={"finance": "view"},
    )

    response = await client.get(_pulse_url(organization_id))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert {kpi["module"] for kpi in payload["kpis"]} == {"finance"}
    assert payload["health"] == {
        "status": "good",
        "modules_with_data": 1,
        "modules_total": 1,
    }
    # Le fil d'activité est réservé aux admins.
    assert payload["activity"] == []


@pytest.mark.asyncio
async def test_sante_en_alerte_quand_un_module_visible_est_vide(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_keys(db_session, organization_id, ["finance.revenue", "finance.margin"])

    response = await client.get(_pulse_url(organization_id))

    assert response.status_code == 200, response.text
    health = response.json()["health"]
    assert health == {"status": "warning", "modules_with_data": 1, "modules_total": 4}


@pytest.mark.asyncio
async def test_sante_inconnue_sans_module_visible(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    await invite_and_accept(
        app, client, organization_id=organization_id, email="sans-droit@example.com"
    )

    response = await client.get(_pulse_url(organization_id))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["kpis"] == []
    assert payload["health"] == {
        "status": "unknown",
        "modules_with_data": 0,
        "modules_total": 0,
    }


@pytest.mark.asyncio
async def test_aucune_donnee_renvoie_des_kpi_vides(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    response = await client.get(_pulse_url(organization_id))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["kpis"] == []
    # Les modules visibles existent mais ne sont pas alimentés : alerte, pas inconnu.
    assert payload["health"]["status"] == "warning"
    assert payload["health"]["modules_total"] == 4


@pytest.mark.asyncio
async def test_admin_voit_le_fil_d_activite(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    invited = await invite(client, organization_id, email="invite@example.com")
    assert invited.status_code == 201, invited.text

    response = await client.get(_pulse_url(organization_id))

    assert response.status_code == 200, response.text
    actions = [entry["action"] for entry in response.json()["activity"]]
    assert "invitation.created" in actions


@pytest.mark.asyncio
async def test_inconnu_d_une_autre_organisation_recoit_403(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await register_admin(client, email="proprio@example.com")
    await register_admin(client, email="intrus@example.com")

    response = await client.get(_pulse_url(organization_id))

    assert response.status_code == 403
