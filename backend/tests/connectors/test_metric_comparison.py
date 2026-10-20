"""Tests de l'endpoint de comparaison de périodes (phase 6a).

Couvre : répartition des points entre les deux fenêtres, agrégation selon le type
de métrique (flux → somme, niveau → dernière valeur, taux → moyenne), écart et
pourcentage, filtrage par droits, refus hors organisation, clé invalide et
absence de donnée. Les points sont rangés en base (tenant posé) avant lecture
via l'API (RLS réelle).
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
from tests.helpers import invite_and_accept, register_admin

# Fenêtre de test : 10 points quotidiens (valeurs 1 → 10), 5 jours de chaque côté.
_DAY0 = datetime(2026, 10, 3, 0, 0, tzinfo=UTC)
_END = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
_DAYS = 5


def _comparison_url(organization_id: uuid.UUID, metric_key: str) -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/metrics/{metric_key}/comparison"


async def _seed(
    db_session: AsyncSession, organization_id: uuid.UUID, metric_key: str, unit: str
) -> None:
    """Range 10 points quotidiens (valeurs 1 → 10) pour la clé donnée."""
    await set_tenant(db_session, organization_id=organization_id)
    snapshots = [
        MetricSnapshotIn(
            metric_key=metric_key,
            unit=unit,
            period="P1D",
            value=float(offset + 1),
            captured_at=_DAY0 + timedelta(days=offset),
        )
        for offset in range(10)
    ]
    await metric_snapshots_repository.upsert_many(db_session, organization_id, snapshots)
    await db_session.commit()


async def _get(
    client: httpx.AsyncClient, organization_id: uuid.UUID, metric_key: str
) -> httpx.Response:
    return await client.get(
        _comparison_url(organization_id, metric_key),
        params={"days": 5, "end": _END.isoformat()},
    )


@pytest.mark.asyncio
async def test_flux_agrege_par_somme(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR")

    response = await _get(client, organization_id, "finance.revenue")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["aggregation"] == "sum"
    # Fenêtre courante = 6+7+8+9+10, précédente = 1+2+3+4+5.
    assert [point["value"] for point in payload["current"]] == [6, 7, 8, 9, 10]
    assert [point["value"] for point in payload["previous"]] == [1, 2, 3, 4, 5]
    assert payload["summary"] == {
        "current_value": 40.0,
        "previous_value": 15.0,
        "change": 25.0,
        "change_percent": pytest.approx(166.67),
    }


@pytest.mark.asyncio
async def test_niveau_agrege_par_derniere_valeur(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.cash", "EUR")

    response = await _get(client, organization_id, "finance.cash")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["aggregation"] == "last"
    assert payload["summary"]["current_value"] == 10.0
    assert payload["summary"]["previous_value"] == 5.0
    assert payload["summary"]["change"] == 5.0
    assert payload["summary"]["change_percent"] == 100.0


@pytest.mark.asyncio
async def test_taux_agrege_par_moyenne(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "projects.avg_progress", "%")

    response = await _get(client, organization_id, "projects.avg_progress")

    assert response.status_code == 200, response.text
    summary = response.json()["summary"]
    assert response.json()["aggregation"] == "average"
    # Moyenne de 6..10 = 8 ; moyenne de 1..5 = 3.
    assert summary["current_value"] == 8.0
    assert summary["previous_value"] == 3.0
    assert summary["change"] == 5.0


@pytest.mark.asyncio
async def test_periode_precedente_nulle_donne_un_pourcentage_absent(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    """Un dénominateur nul n'a pas de pourcentage : le champ vaut `null`."""
    organization_id = await register_admin(client)
    await set_tenant(db_session, organization_id=organization_id)
    await metric_snapshots_repository.upsert_many(
        db_session,
        organization_id,
        [
            MetricSnapshotIn(
                metric_key="finance.cash",
                unit="EUR",
                period="P1D",
                value=0.0,
                captured_at=_DAY0 + timedelta(days=offset),
            )
            for offset in range(5)
        ],
    )
    await db_session.commit()

    response = await _get(client, organization_id, "finance.cash")

    assert response.status_code == 200, response.text
    assert response.json()["summary"]["change_percent"] is None


@pytest.mark.asyncio
async def test_un_membre_sans_droit_recoit_403(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR")
    await invite_and_accept(
        app, client, organization_id=organization_id, email="membre@example.com"
    )

    response = await _get(client, organization_id, "finance.revenue")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_un_membre_avec_vue_lit_la_comparaison(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed(db_session, organization_id, "finance.revenue", "EUR")
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="compta@example.com",
        modules={"finance": "view"},
    )

    assert (await _get(client, organization_id, "finance.revenue")).status_code == 200
    # Le module web n'a pas été accordé.
    assert (await _get(client, organization_id, "web.visitors")).status_code == 403


@pytest.mark.asyncio
async def test_inconnu_d_une_autre_organisation_recoit_403(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client, email="proprio@example.com")
    await _seed(db_session, organization_id, "finance.revenue", "EUR")
    await register_admin(client, email="intrus@example.com")

    assert (await _get(client, organization_id, "finance.revenue")).status_code == 403


@pytest.mark.asyncio
async def test_cle_invalide_recoit_422(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    response = await client.get(_comparison_url(organization_id, "pas-une-cle"))

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_days_hors_bornes_recoit_422(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    response = await client.get(
        _comparison_url(organization_id, "finance.revenue"), params={"days": 0}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_serie_sans_donnee_recoit_404(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)

    response = await _get(client, organization_id, "finance.revenue")

    assert response.status_code == 404
