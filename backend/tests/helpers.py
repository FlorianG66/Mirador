"""Outils de test partagés (invitations, permissions, audit, connexion Google)."""

from __future__ import annotations

import re
import uuid
from datetime import date
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import API_PREFIX, CSRF_COOKIE
from app.core.tenancy import set_tenant
from app.services.legal_registry import LegalCompany, LegalLeader, LegalRegistryError
from app.services.oidc import OidcIdentity, OidcProviderError
from tests.conftest import register_client

PASSWORD = "mot-de-passe-secret"

# L'API renvoie toujours les cinq modules : soit tous en `edit` (admin), soit tous
# au niveau choisi/par défaut (`none`).
ADMIN_MODULES: dict[str, str] = {
    "finance": "edit",
    "web": "edit",
    "social": "edit",
    "projects": "edit",
    "legal": "edit",
}
EMPTY_MODULES: dict[str, str] = {
    "finance": "none",
    "web": "none",
    "social": "none",
    "projects": "none",
    "legal": "none",
}


def modules_with(**levels: str) -> dict[str, str]:
    """Niveaux complets des cinq modules, avec les surcharges passées en argument."""
    return {**EMPTY_MODULES, **levels}


class FakeEmailSender:
    """Capture les e-mails : les assertions portent sur le contenu, sans SMTP."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, *, to: str, subject: str, content: str) -> None:
        self.sent.append((to, subject, content))


class FakeOidcProvider:
    """Fournisseur OIDC de test : aucune requête réseau, tout tient en mémoire.

    L'URL d'autorisation est conservée pour que les tests lisent l'état et le
    redirect_uri réellement envoyés ; `exchange_calls` journalise les échanges.
    """

    def __init__(
        self, identity: OidcIdentity | None = None, *, error: OidcProviderError | None = None
    ) -> None:
        self.identity = identity or OidcIdentity(
            subject="google-subject", email="admin@example.com", email_verified=True, name="Ada"
        )
        self.error = error
        self.authorization_urls: list[str] = []
        self.exchange_calls: list[tuple[str, str]] = []

    def authorization_url(self, *, state: str, redirect_uri: str) -> str:
        query = urlencode(
            {
                "client_id": "client-de-test",
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
            }
        )
        url = f"https://accounts.example.test/o/oauth2/v2/auth?{query}"
        self.authorization_urls.append(url)
        return url

    async def exchange_code(self, *, code: str, redirect_uri: str) -> OidcIdentity:
        self.exchange_calls.append((code, redirect_uri))
        if self.error is not None:
            raise self.error
        return self.identity


def install_oidc(
    app: FastAPI, identity: OidcIdentity | None = None, *, error: OidcProviderError | None = None
) -> FakeOidcProvider:
    """Branche un fournisseur factice sur l'application sous test."""
    provider = FakeOidcProvider(identity, error=error)
    app.state.oidc_provider = provider
    return provider


# SIREN et SIRET valides (clé de Luhn) servant d'exemples dans les tests légaux.
SIREN_VALIDE = "732829320"
SIRET_VALIDE = "73282932000017"


def sample_company(**overrides: object) -> LegalCompany:
    """Fiche d'entreprise fictive, surchargeable champ par champ pour les tests."""
    defaults: dict[str, object] = {
        "siren": SIREN_VALIDE,
        "source": "registry",
        "diffusable": True,
        "siret_siege": SIRET_VALIDE,
        "raison_sociale": "ACME FICTIVE",
        "nom_commercial": "Acme",
        "forme_juridique": "5710",
        "date_creation": date(2010, 1, 1),
        "code_naf": "62.01Z",
        "libelle_naf": "Programmation informatique",
        "adresse": "1 rue Fictive, 75001 Paris",
        "tranche_effectif": "11",
        "dirigeants": (LegalLeader(nom="Ada Fictive", qualite="Présidente"),),
    }
    return LegalCompany(**{**defaults, **overrides})  # type: ignore[arg-type]


class FakeLegalRegistry:
    """Registre d'identité légale de test : aucun réseau, résultats pilotés en mémoire."""

    def __init__(
        self,
        *,
        companies: list[LegalCompany] | None = None,
        error: LegalRegistryError | None = None,
    ) -> None:
        self.error = error
        self.companies: dict[str, LegalCompany] = {
            company.siren: company for company in (companies or [])
        }
        self.calls: list[str] = []

    async def fetch_by_siren(self, siren: str) -> LegalCompany | None:
        self.calls.append(siren)
        if self.error is not None:
            raise self.error
        return self.companies.get(siren)


def install_legal_registry(
    app: FastAPI,
    *,
    companies: list[LegalCompany] | None = None,
    error: LegalRegistryError | None = None,
) -> FakeLegalRegistry:
    """Branche un registre légal factice sur l'application sous test."""
    registry = FakeLegalRegistry(companies=companies, error=error)
    app.state.legal_registry = registry
    return registry


def csrf_headers(client: httpx.AsyncClient) -> dict[str, str]:
    """En-tête attendu par le middleware CSRF pour une écriture authentifiée."""
    return {"x-csrf-token": client.cookies.get(CSRF_COOKIE, "")}


async def register_admin(
    client: httpx.AsyncClient, *, email: str = "admin@example.com"
) -> uuid.UUID:
    """Inscription de l'admin courant : retourne l'identifiant de son organisation."""
    response = await register_client(client, email=email)
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["organization"]["id"])


async def login(client: httpx.AsyncClient, email: str) -> httpx.Response:
    """Connexion avec le mot de passe de test partagé : remplace la session courante."""
    return await client.post(
        f"{API_PREFIX}/auth/login", json={"email": email, "password": PASSWORD}
    )


def extract_invitation_link(content: str) -> tuple[str, str]:
    """Récupère (jeton, organisation) dans le lien d'acceptation de l'e-mail."""
    match = re.search(r"accept\?token=([^\s&]+)&organization=([^\s]+)", content)
    assert match is not None, "l'e-mail doit contenir le lien d'acceptation"
    return match.group(1), match.group(2)


async def invite(
    client: httpx.AsyncClient,
    organization_id: uuid.UUID,
    *,
    email: str,
    modules: dict[str, str] | None = None,
    role: str = "member",
) -> httpx.Response:
    """Invitation émise par l'admin actuellement connecté sur `client`."""
    return await client.post(
        f"{API_PREFIX}/organizations/{organization_id}/invitations",
        json={"email": email, "role": role, "modules": modules or {}},
        headers=csrf_headers(client),
    )


async def invite_and_accept(
    app: FastAPI,
    client: httpx.AsyncClient,
    *,
    organization_id: uuid.UUID,
    email: str,
    modules: dict[str, str] | None = None,
    role: str = "member",
) -> httpx.Response:
    """Invite `email` puis laisse la session de l'invité sur `client`.

    L'e-mail envoyé reste consultable via `app.state.email_sender.sent[-1]`.
    """
    sender = FakeEmailSender()
    app.state.email_sender = sender
    invited = await invite(client, organization_id, email=email, modules=modules, role=role)
    assert invited.status_code == 201, invited.text
    token, organization = extract_invitation_link(sender.sent[-1][2])
    client.cookies.clear()
    registered = await register_client(client, email=email)
    assert registered.status_code == 201, registered.text
    accepted = await client.post(
        f"{API_PREFIX}/auth/invitations/accept",
        json={"token": token, "organization_id": organization},
        headers=csrf_headers(client),
    )
    assert accepted.status_code == 201, accepted.text
    return accepted


async def audit_actions(
    session_factory: async_sessionmaker[AsyncSession], organization_id: uuid.UUID
) -> list[str]:
    """Actions journalisées pour l'organisation (RLS : le tenant doit être posé)."""
    async with session_factory() as session:
        await set_tenant(session, organization_id=organization_id)
        result = await session.execute(text("SELECT action FROM audit_logs ORDER BY created_at"))
        return list(result.scalars().all())
