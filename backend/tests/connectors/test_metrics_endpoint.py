"""Tests de l'endpoint de lecture des métriques (phase 4d).

Couvre : lecture admin, filtre par fenêtre/limite, refus par granularité de
permission (module `view` requis), refus hors organisation, clé invalide, et
bornes temporelles inversées. Les données sont synchronisées en base (tenant
posé) avant d'être lues via l'API (RLS réelle).
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
from app.services.sync import sync_organization
from tests.helpers import invite_and_accept, register_admin


async def _seed_metrics(db_session: AsyncSession, organization_id: uuid.UUID) -> None:
    """Range les séries fictives de l'organisation en base (worker de test)."""
    await set_tenant(db_session, organization_id=organization_id)
    await sync_organization(db_session, organization_id)
    await db_session.commit()


def _metrics_url(organization_id: uuid.UUID, metric_key: str) -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/metrics/{metric_key}"


@pytest.mark.asyncio
async def test_admin_lit_une_serie(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_metrics(db_session, organization_id)

    response = await client.get(_metrics_url(organization_id, "finance.revenue"))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["key"] == "finance.revenue"
    assert payload["unit"] == "EUR"
    assert payload["period"] == "P1D"
    assert payload["points"]
    # Tri chronologique : la valeur doit être une série réelle et stable.
    ats = [datetime.fromisoformat(point["at"]) for point in payload["points"]]
    assert ats == sorted(ats)


@pytest.mark.asyncio
async def test_fenetre_de_dates_filtre_les_points(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_metrics(db_session, organization_id)

    start = (datetime.now(UTC) - timedelta(days=10)).date().isoformat()
    end = (datetime.now(UTC) - timedelta(days=8)).date().isoformat()
    response = await client.get(
        _metrics_url(organization_id, "finance.revenue"),
        params={"start": start, "end": end},
    )

    assert response.status_code == 200, response.text
    points = response.json()["points"]
    assert points
    assert all(start <= point["at"][:10] <= end for point in points)


@pytest.mark.asyncio
async def test_la_limite_borne_le_nombre_de_points(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_metrics(db_session, organization_id)

    response = await client.get(
        _metrics_url(organization_id, "finance.revenue"), params={"limit": 3}
    )

    assert response.status_code == 200, response.text
    assert len(response.json()["points"]) <= 3


@pytest.mark.asyncio
async def test_un_membre_sans_droit_recoit_403(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_metrics(db_session, organization_id)
    await invite_and_accept(
        app, client, organization_id=organization_id, email="membre@example.com"
    )

    response = await client.get(_metrics_url(organization_id, "finance.revenue"))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_un_membre_avec_vue_lit_la_serie(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_metrics(db_session, organization_id)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="compta@example.com",
        modules={"finance": "view"},
    )

    response = await client.get(_metrics_url(organization_id, "finance.revenue"))

    assert response.status_code == 200, response.text
    # Le module web n'a pas été accordé : il reste interdit.
    assert (await client.get(_metrics_url(organization_id, "web.visits"))).status_code == 403


@pytest.mark.asyncio
async def test_inconnu_d_une_autre_organisation_recoit_403(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client, email="proprio@example.com")
    await _seed_metrics(db_session, organization_id)
    # Un autre compte, propriétaire de sa propre organisation : la session change.
    await register_admin(client, email="intrus@example.com")

    response = await client.get(_metrics_url(organization_id, "finance.revenue"))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cle_non_canonique_recoit_422(client: httpx.AsyncClient, app: FastAPI) -> None:
    organization_id = await register_admin(client)

    response = await client.get(_metrics_url(organization_id, "pas-une-cle"))

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_borne_inversee_recoit_422(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_metrics(db_session, organization_id)

    response = await client.get(
        _metrics_url(organization_id, "finance.revenue"),
        params={"start": "2026-10-01", "end": "2026-09-01"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_serie_sans_donnee_recoit_404(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    response = await client.get(_metrics_url(organization_id, "finance.revenue"))

    assert response.status_code == 404
