"""Service d'authentification : inscription (compte + organisation) et vérification."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.core.tenancy import set_tenant
from app.models.enums import Role
from app.models.organization import Organization
from app.models.user import User
from app.repositories import memberships, organizations, users
from app.services.errors import ServiceProblem
from app.services.oidc import OidcIdentity

# Hachage factice vérifié quand le compte est inconnu : le temps de calcul ne
# trahit pas l'existence de l'e-mail (aucune énumération par minutage).
_DUMMY_DIGEST = hash_password("compte-inexistant-placeholder")


class EmailAlreadyUsed(Exception):
    """Un compte porte déjà cet e-mail."""


async def register(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    organization_name: str,
    siren: str | None = None,
) -> tuple[User, Organization]:
    """Crée le compte, son organisation et le rattachement admin, en une requête.

    L'ordre compte : la table `users` est globale (hors RLS), mais l'insertion du
    membership exige le tenant posé — d'où `set_tenant` avant le membership.
    """
    if await users.get_user_by_email(session, email) is not None:
        raise EmailAlreadyUsed from None
    organization = await organizations.create_organization(
        session, name=organization_name, siren=siren
    )
    try:
        user = await users.create_user(session, email=email, password_hash=hash_password(password))
        await set_tenant(session, user_id=user.id, organization_id=organization.id)
        await memberships.create_membership(
            session,
            organization_id=organization.id,
            user_id=user.id,
            role=Role.ADMIN,
        )
        await session.flush()
    except IntegrityError:
        # Course possible avec une inscription simultanée : la contrainte tranche.
        await session.rollback()
        raise EmailAlreadyUsed from None
    return user, organization


async def authenticate(session: AsyncSession, *, email: str, password: str) -> User | None:
    """Vérifie les identifiants ; None si le compte est absent, sans mot de passe
    (compte Google) ou si le mot de passe ne correspond pas."""
    user = await users.get_user_by_email(session, email)
    digest = user.password_hash if user is not None else None
    if digest is None:
        verify_password(password, _DUMMY_DIGEST)  # temps de calcul identique
        return None
    if not verify_password(password, digest):
        return None
    return user


async def authenticate_google(session: AsyncSession, *, identity: OidcIdentity) -> User:
    """Rattache une identité Google à un compte existant (jamais de création ici).

    L'e-mail non vérifié est refusé : seules les adresses confirmées par Google
    ouvrent une session. La création de compte reste du domaine des invitations
    (phase 2d) — voir docs/DECISIONS.md.
    """
    if not identity.email_verified:
        raise ServiceProblem(403, "Adresse e-mail Google non vérifiée.")
    user = await users.get_user_by_email(session, identity.email)
    if user is None:
        raise ServiceProblem(403, "Aucun compte n'est associé à cette adresse e-mail.")
    return user
