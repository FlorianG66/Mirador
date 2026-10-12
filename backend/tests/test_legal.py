"""Tests de la fiche légale (phase 5e).

Couvre : lecture (admin, membre sans droit, membre `view`), saisie manuelle marquée
`manual` (qui prime sur le registre), validation SIREN/SIRET, rafraîchissement depuis
un registre factice (pré-remplissage, SIREN inconnu, registre injoignable),
masquage des dirigeants pour un membre non-admin, calcul de la TVA, isolation entre
organisations. Le registre est toujours simulé (`install_legal_registry`) : aucun
appel réseau.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import API_PREFIX
from app.core.tenancy import set_tenant
from app.models.legal_profile import LegalProfile
from app.services.legal_registry import LegalRegistryError
from tests.conftest import seed_organization_with_admin
from tests.helpers import (
    SIREN_VALIDE,
    audit_actions,
    csrf_headers,
    install_legal_registry,
    invite_and_accept,
    register_client,
    sample_company,
)


async def _register_admin_with_siren(
    client: httpx.AsyncClient, *, siren: str = SIREN_VALIDE, email: str = "admin@example.com"
) -> uuid.UUID:
    """Inscription d'un admin dont l'organisation porte déjà un SIREN."""
    response = await register_client(client, email=email, siren=siren)
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["organization"]["id"])


def _legal_url(organization_id: uuid.UUID, suffix: str = "") -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/legal{suffix}"


@pytest.mark.asyncio
async def test_admin_lit_une_fiche_vide(client: httpx.AsyncClient) -> None:
    organization_id = await _register_admin_with_siren(client)

    response = await client.get(_legal_url(organization_id))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["siren"] == SIREN_VALIDE
    assert payload["raison_sociale"] is None
    assert payload["sources"] == {}
    assert payload["identifiers"] == []


@pytest.mark.asyncio
async def test_le_siren_de_l_inscription_apparait_dans_la_fiche(
    client: httpx.AsyncClient,
) -> None:
    organization_id = await _register_admin_with_siren(client, siren=SIREN_VALIDE)

    response = await client.get(_legal_url(organization_id))

    assert response.status_code == 200, response.text
    assert response.json()["siren"] == SIREN_VALIDE


@pytest.mark.asyncio
async def test_membre_sans_droit_legal_recoit_403(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await _register_admin_with_siren(client)
    await invite_and_accept(
        app, client, organization_id=organization_id, email="membre@example.com"
    )

    response = await client.get(_legal_url(organization_id))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_membre_avec_vue_lit_mais_ne_peut_pas_ecrire(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await _register_admin_with_siren(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="juriste@example.com",
        modules={"legal": "view"},
    )

    assert (await client.get(_legal_url(organization_id))).status_code == 200
    update = await client.put(
        _legal_url(organization_id),
        json={"capital_social": "1000 EUR"},
        headers=csrf_headers(client),
    )
    assert update.status_code == 403
    refresh = await client.post(
        _legal_url(organization_id, "/refresh"), headers=csrf_headers(client)
    )
    assert refresh.status_code == 403


@pytest.mark.asyncio
async def test_membre_avec_edit_peut_saisir(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await _register_admin_with_siren(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="compta@example.com",
        modules={"legal": "edit"},
    )

    response = await client.put(
        _legal_url(organization_id),
        json={"capital_social": "1000 EUR"},
        headers=csrf_headers(client),
    )

    assert response.status_code == 200, response.text
    assert response.json()["capital_social"] == "1000 EUR"


@pytest.mark.asyncio
async def test_la_saisie_manuelle_est_marquee_manual(client: httpx.AsyncClient) -> None:
    organization_id = await _register_admin_with_siren(client)

    response = await client.put(
        _legal_url(organization_id),
        json={"capital_social": "1000 EUR"},
        headers=csrf_headers(client),
    )

    assert response.status_code == 200, response.text
    sources = response.json()["sources"]
    assert sources["capital_social"]["source"] == "manual"
    assert sources["capital_social"]["synced_at"] is not None


@pytest.mark.asyncio
async def test_siren_invalide_recoit_422(client: httpx.AsyncClient) -> None:
    organization_id = await _register_admin_with_siren(client)

    response = await client.put(
        _legal_url(organization_id),
        json={"siren": "123456789"},
        headers=csrf_headers(client),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_siret_invalide_recoit_422(client: httpx.AsyncClient) -> None:
    organization_id = await _register_admin_with_siren(client)

    response = await client.put(
        _legal_url(organization_id),
        json={"siret_siege": "123"},
        headers=csrf_headers(client),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_la_tva_est_calculee_depuis_le_siren(client: httpx.AsyncClient) -> None:
    organization_id = await _register_admin_with_siren(client)

    response = await client.put(
        _legal_url(organization_id),
        json={"siren": SIREN_VALIDE},
        headers=csrf_headers(client),
    )

    assert response.status_code == 200, response.text
    vat = [item for item in response.json()["identifiers"] if item["schema"] == "vat"]
    assert vat and vat[0]["valeur"] == "FR44732829320"
    assert vat[0]["source"] == "computed"


@pytest.mark.asyncio
async def test_rafraichissement_preremplit_depuis_le_registre(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await _register_admin_with_siren(client)
    install_legal_registry(app, companies=[sample_company()])

    response = await client.post(
        _legal_url(organization_id, "/refresh"), headers=csrf_headers(client)
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["raison_sociale"] == "ACME FICTIVE"
    assert payload["adresse_siege"] == "1 rue Fictive, 75001 Paris"
    assert payload["sources"]["raison_sociale"]["source"] == "registry"
    assert payload["dirigeants"][0]["nom"] == "Ada Fictive"
    assert any(item["schema"] == "vat" for item in payload["identifiers"])


@pytest.mark.asyncio
async def test_rafraichissement_sans_siren_recoit_400(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    response = await register_client(client, email="sans-siren@example.com")
    assert response.status_code == 201, response.text
    organization_id = uuid.UUID(response.json()["organization"]["id"])
    install_legal_registry(app, companies=[])

    refresh = await client.post(
        _legal_url(organization_id, "/refresh"), headers=csrf_headers(client)
    )

    assert refresh.status_code == 400


@pytest.mark.asyncio
async def test_siren_inconnu_recoit_404(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await _register_admin_with_siren(client)
    install_legal_registry(app, companies=[])

    response = await client.post(
        _legal_url(organization_id, "/refresh"), headers=csrf_headers(client)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_registre_injoignable_recoit_502(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await _register_admin_with_siren(client)
    install_legal_registry(app, error=LegalRegistryError("boom"))

    response = await client.post(
        _legal_url(organization_id, "/refresh"), headers=csrf_headers(client)
    )

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_la_saisie_manuelle_prime_sur_le_registre(
    app: FastAPI, client: httpx.AsyncClient, session_factory: async_sessionmaker
) -> None:
    organization_id = await _register_admin_with_siren(client)
    await client.put(
        _legal_url(organization_id),
        json={"raison_sociale": "MA SOCIETE FICTIVE"},
        headers=csrf_headers(client),
    )
    install_legal_registry(app, companies=[sample_company(raison_sociale="AUTRE NOM")])

    response = await client.post(
        _legal_url(organization_id, "/refresh"), headers=csrf_headers(client)
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["raison_sociale"] == "MA SOCIETE FICTIVE"
    assert payload["sources"]["raison_sociale"]["source"] == "manual"
    actions = await audit_actions(session_factory, organization_id)
    assert "legal.profile.diverged" in actions


@pytest.mark.asyncio
async def test_un_changement_de_registre_met_a_jour_le_champ(
    app: FastAPI, client: httpx.AsyncClient, session_factory: async_sessionmaker
) -> None:
    organization_id = await _register_admin_with_siren(client)
    registry = install_legal_registry(app, companies=[sample_company()])
    await client.post(_legal_url(organization_id, "/refresh"), headers=csrf_headers(client))

    registry.companies[SIREN_VALIDE] = sample_company(raison_sociale="NOUVEAU NOM")
    response = await client.post(
        _legal_url(organization_id, "/refresh"), headers=csrf_headers(client)
    )

    assert response.status_code == 200, response.text
    assert response.json()["raison_sociale"] == "NOUVEAU NOM"
    actions = await audit_actions(session_factory, organization_id)
    assert actions.count("legal.profile.refreshed") == 2


@pytest.mark.asyncio
async def test_entreprise_non_diffusable_masque_dirigeants_et_adresse(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await _register_admin_with_siren(client)
    company = sample_company(diffusable=False, adresse=None, dirigeants=())
    install_legal_registry(app, companies=[company])

    response = await client.post(
        _legal_url(organization_id, "/refresh"), headers=csrf_headers(client)
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["adresse_siege"] is None
    assert payload["dirigeants"] == []


@pytest.mark.asyncio
async def test_un_membre_vue_ne_voit_pas_les_dirigeants(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    organization_id = await _register_admin_with_siren(client)
    install_legal_registry(app, companies=[sample_company()])
    await client.post(_legal_url(organization_id, "/refresh"), headers=csrf_headers(client))
    # L'admin voit les dirigeants…
    assert (await client.get(_legal_url(organization_id))).json()["dirigeants"]

    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="membre2@example.com",
        modules={"legal": "view"},
    )

    response = await client.get(_legal_url(organization_id))

    assert response.status_code == 200, response.text
    assert response.json()["dirigeants"] == []


@pytest.mark.asyncio
async def test_un_inconnu_d_une_autre_organisation_recoit_403(
    client: httpx.AsyncClient,
) -> None:
    organization_id = await _register_admin_with_siren(client, email="proprio@example.com")
    await _register_admin_with_siren(client, email="intrus@example.com")

    response = await client.get(_legal_url(organization_id))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_un_tenant_ne_lit_pas_la_fiche_d_un_autre(db_session: AsyncSession) -> None:
    """Défense en profondeur : la RLS isole les fiches légales entre organisations."""
    alpha_id, _ = await seed_organization_with_admin(
        db_session, name="Alpha", email="alpha@legal.test"
    )
    beta_id, _ = await seed_organization_with_admin(
        db_session, name="Beta", email="beta@legal.test"
    )
    await set_tenant(db_session, organization_id=alpha_id)
    db_session.add(LegalProfile(organization_id=alpha_id, raison_sociale="Alpha SARL"))
    await db_session.flush()

    await set_tenant(db_session, organization_id=beta_id)
    result = await db_session.execute(
        select(LegalProfile).where(LegalProfile.organization_id == alpha_id)
    )

    assert result.scalars().all() == []
