"""Mode démo (SPEC §9) : scénarios, provisionnement, liens et remise à zéro.

Chaque session crée une organisation `is_demo` **à part** : le visiteur obtient sa
propre entreprise fictive, alimentée par les MockConnectors, et la purge supprime
tout à l'échéance. Aucune donnée réelle n'est lue ni écrite, et le registre légal
n'est jamais appelé : la fiche est fabriquée ici, avec des identifiants signalés
comme fictifs (`000000000`, mentions « fictif »).

Les liens `/demo/<token>` sont des capacités : seul leur hachage est stocké, comme
pour les sessions et les invitations. Ils expirent indépendamment de la session
qu'ils ouvrent, et peuvent être utilisés plusieurs fois jusqu'à leur échéance
(chaque ouverture reste isolée dans sa propre organisation).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_token, hash_token
from app.core.tenancy import set_tenant
from app.models.enums import DemoSector, Role
from app.models.legal_profile import LEGAL_PROFILE_FIELDS, LegalProfile
from app.models.organization import Organization
from app.models.user import User
from app.repositories import demo_links as demo_links_repository
from app.repositories import legal_profiles as legal_profiles_repository
from app.repositories import memberships as memberships_repository
from app.repositories import organizations as organizations_repository
from app.repositories import users as users_repository
from app.services.errors import ServiceProblem
from app.services.sync import sync_organization

# Domaine réservé par la RFC 2606 (documentation) : aucune boîte ne peut exister
# derrière, et il n'est pas dans la liste des domaines « special-use » refusés par
# la validation d'e-mail. Aucun compte démo n'a de mot de passe : il ne peut donc
# pas être repris par une connexion classique.
DEMO_EMAIL_DOMAIN = "example.com"
# SIREN/SIRET fictifs, volontairement invalides au sens de la clé de Luhn.
FICTIONAL_SIREN = "000000000"
FICTIONAL_SIRET = "00000000000000"


@dataclass(frozen=True)
class DemoScenario:
    """Un scénario sectoriel complet, prêt à être semé dans une organisation."""

    sector: DemoSector
    organization_name: str
    raison_sociale: str
    nom_commercial: str
    forme_juridique: str
    code_naf: str
    libelle_naf: str
    adresse_siege: str
    tranche_effectif: str
    capital_social: str
    rcs_greffe: str
    dirigeants: tuple[dict[str, str], ...]


_SCENARIOS: dict[DemoSector, DemoScenario] = {
    DemoSector.RESTAURANT: DemoScenario(
        sector=DemoSector.RESTAURANT,
        organization_name="Maison Fictive — Démo",
        raison_sociale="MAISON FICTIVE (ENTREPRISE FICTIVE — DÉMO)",
        nom_commercial="Maison Fictive",
        forme_juridique="SARL (fictive)",
        code_naf="56.10A",
        libelle_naf="Restauration traditionnelle",
        adresse_siege="12 rue de la Démonstration, 75011 Paris — adresse fictive",
        tranche_effectif="11",
        capital_social="10 000 € (fictif)",
        rcs_greffe="RCS Paris fictif",
        dirigeants=({"nom": "Camille Fictive", "qualite": "Gérante"},),
    ),
    DemoSector.AGENCY: DemoScenario(
        sector=DemoSector.AGENCY,
        organization_name="Studio Fictif — Démo",
        raison_sociale="STUDIO FICTIF (ENTREPRISE FICTIVE — DÉMO)",
        nom_commercial="Studio Fictif",
        forme_juridique="SAS (fictive)",
        code_naf="62.01Z",
        libelle_naf="Programmation informatique",
        adresse_siege="8 avenue de la Démonstration, 69002 Lyon — adresse fictive",
        tranche_effectif="12",
        capital_social="5 000 € (fictif)",
        rcs_greffe="RCS Lyon fictif",
        dirigeants=({"nom": "Alex Fictif", "qualite": "Président"},),
    ),
    DemoSector.ECOMMERCE: DemoScenario(
        sector=DemoSector.ECOMMERCE,
        organization_name="Boutique Fictive — Démo",
        raison_sociale="BOUTIQUE FICTIVE (ENTREPRISE FICTIVE — DÉMO)",
        nom_commercial="Boutique Fictive",
        forme_juridique="SAS (fictive)",
        code_naf="47.91B",
        libelle_naf="Vente à distance sur catalogue spécialisé",
        adresse_siege="3 place de la Démonstration, 33000 Bordeaux — adresse fictive",
        tranche_effectif="11",
        capital_social="20 000 € (fictif)",
        rcs_greffe="RCS Bordeaux fictif",
        dirigeants=({"nom": "Morgane Fictive", "qualite": "Directrice"},),
    ),
}


def list_scenarios() -> list[DemoScenario]:
    """Scénarios proposés sur `/demo`, dans un ordre stable."""
    return [_SCENARIOS[sector] for sector in DemoSector]


def get_scenario(sector: DemoSector | str) -> DemoScenario:
    """Scénario du secteur demandé ; 404 si le secteur est inconnu."""
    resolved = DemoSector(sector)
    scenario = _SCENARIOS.get(resolved)
    if scenario is None:  # pragma: no cover - DemoSector couvre déjà la liste
        raise ServiceProblem(404, "Scénario de démonstration inconnu.")
    return scenario


async def create_demo_session(
    session: AsyncSession, *, sector: DemoSector, ttl_minutes: int
) -> tuple[User, Organization, datetime]:
    """Crée une organisation fictive isolée, son admin et ses données de démo.

    L'ordre importe : le tenant doit être posé avant toute écriture soumise à la
    RLS (membership, fiche légale, métriques). Aucun mot de passe n'est créé.
    """
    scenario = get_scenario(sector)
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=ttl_minutes)
    organization = await organizations_repository.create_organization(
        session,
        name=scenario.organization_name,
        is_demo=True,
        demo_sector=scenario.sector.value,
        demo_expires_at=expires_at,
    )
    user = await users_repository.create_user(
        session,
        email=f"demo+{uuid.uuid4().hex}@{DEMO_EMAIL_DOMAIN}",
        password_hash=None,
    )
    await set_tenant(session, user_id=user.id, organization_id=organization.id)
    await memberships_repository.create_membership(
        session,
        organization_id=organization.id,
        user_id=user.id,
        role=Role.ADMIN,
    )
    await _seed_legal_profile(session, organization_id=organization.id, scenario=scenario, now=now)
    await sync_organization(session, organization.id)
    return user, organization, expires_at


async def _seed_legal_profile(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    scenario: DemoScenario,
    now: datetime,
) -> LegalProfile:
    """Fiche légale fictive, signalée comme telle ; jamais issue d'un registre."""
    profile = legal_profiles_repository.create(session, organization_id)
    profile.siren = FICTIONAL_SIREN
    profile.siret_siege = FICTIONAL_SIRET
    profile.raison_sociale = scenario.raison_sociale
    profile.nom_commercial = scenario.nom_commercial
    profile.forme_juridique = scenario.forme_juridique
    profile.date_creation = date(2019, 3, 12)
    profile.code_naf = scenario.code_naf
    profile.libelle_naf = scenario.libelle_naf
    profile.adresse_siege = scenario.adresse_siege
    profile.tranche_effectif = scenario.tranche_effectif
    profile.capital_social = scenario.capital_social
    profile.rcs_greffe = scenario.rcs_greffe
    profile.dirigeants = [dict(director) for director in scenario.dirigeants]
    profile.field_sources = {
        field: {"source": "demo", "synced_at": now.isoformat()} for field in LEGAL_PROFILE_FIELDS
    }
    profile.updated_at = now
    await session.flush()
    return profile


async def create_demo_link(
    session: AsyncSession,
    *,
    sector: DemoSector,
    organization_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    ttl_hours: int,
) -> tuple[str, datetime]:
    """Génère un lien à durée limitée ; retourne le jeton en clair (jamais stocké)."""
    token = generate_token()
    expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
    await demo_links_repository.create_demo_link(
        session,
        sector=sector.value,
        token_hash=hash_token(token),
        expires_at=expires_at,
        organization_id=organization_id,
        created_by_user_id=created_by_user_id,
    )
    return token, expires_at


async def redeem_demo_link(session: AsyncSession, *, token: str) -> DemoSector:
    """Secteur du lien présenté, ou 410 s'il est inconnu ou expiré."""
    link = await demo_links_repository.get_by_token_hash(session, hash_token(token))
    if link is None or link.expires_at <= datetime.now(UTC):
        raise ServiceProblem(410, "Ce lien de démonstration est inconnu ou expiré.")
    return DemoSector(link.sector)


async def purge_expired_demos(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Supprime les organisations démo échues, leurs comptes et leurs données.

    Chaque organisation est traitée avec son tenant posé : `memberships` et les
    tables métier sont sous RLS, et les suppressions en cascade restent lisibles.
    Retourne le nombre d'organisations purgées.
    """
    moment = now or datetime.now(UTC)
    expired = await organizations_repository.list_expired_demo_organizations(session, now=moment)
    for organization in expired:
        await set_tenant(session, organization_id=organization.id)
        members = await memberships_repository.list_members(
            session, organization_id=organization.id
        )
        user_ids = [member.user_id for member in members]
        await session.delete(organization)
        await session.flush()
        for user_id in user_ids:
            user = await session.get(User, user_id)
            if user is not None:
                await session.delete(user)
        await set_tenant(session)
    await demo_links_repository.delete_expired(session, now=moment)
    return len(expired)
