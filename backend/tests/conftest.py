"""Fixtures partagées : application sous test, base PostgreSQL isolée, outils d'Alembic."""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import asyncpg
import httpx
import pgserver
import pytest
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.requests import Request

from alembic import command
from app.core.config import Settings
from app.core.constants import API_PREFIX
from app.core.tenancy import set_tenant
from app.main import create_app
from app.models.enums import Role
from app.repositories import memberships as memberships_repository
from app.repositories import organizations as organizations_repository
from app.repositories import users as users_repository

# URL volontairement injoignable : port 1 = refus de connexion immédiat.
UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://mirador:mirador@127.0.0.1:1/mirador"

BACKEND_ROOT = Path(__file__).parents[1]
# asyncpg parle postgresql:// ; SQLAlchemy utilise postgresql+asyncpg://.
SQLALCHEMY_URL_PREFIX = "postgresql+asyncpg://"
ASYNC_PG_URL_PREFIX = "postgresql://"

# Rôle de test non-superuser : PostgreSQL fait toujours passer un superuser avant
# la RLS, donc sans ce rôle les tests d'isolation ne testeraient rien.
TEST_ROLE = "mirador_test"


def alembic_config(database_url: str) -> Config:
    """Configuration Alembic pointant explicitement sur la base passée."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_to_head(database_url: str) -> None:
    """Applique toutes les migrations sur la base indiquée."""
    command.upgrade(alembic_config(database_url), "head")


def _raw_pg_url(database_url: str) -> str:
    """Convertit une URL SQLAlchemy en URL lisible par asyncpg (changement de schéma)."""
    return database_url.replace(SQLALCHEMY_URL_PREFIX, ASYNC_PG_URL_PREFIX, 1)


def _with_database(database_url: str, database_name: str) -> str:
    """URL du même serveur PostgreSQL mais d'une autre base (isolation des tests d'Alembic)."""
    return database_url.rsplit("/", 1)[0] + "/" + database_name


async def _run_sql(sql: str, database_url: str) -> None:
    """Exécute une instruction utilitaire (CREATE/DROP DATABASE) hors transaction."""
    connection = await asyncpg.connect(_raw_pg_url(database_url))
    try:
        await connection.execute(sql)
    finally:
        await connection.close()


def create_test_database(database_url: str, database_name: str) -> None:
    """Crée une base vierge sur le même serveur (les allers-retours Alembic l'utilisent)."""
    asyncio.run(_run_sql(f"CREATE DATABASE {database_name}", database_url))


def drop_test_database(database_url: str, database_name: str) -> None:
    """Supprime la base de test, y compris ses connexions encore ouvertes (PG13+)."""
    asyncio.run(_run_sql(f"DROP DATABASE {database_name} (FORCE)", database_url))


def fetch_scalar(database_url: str, sql: str) -> object | None:
    """Requête mono-colonne en dehors de l'application, pour les assertions de schéma."""

    async def _fetch() -> object | None:
        connection = await asyncpg.connect(_raw_pg_url(database_url))
        try:
            return await connection.fetchval(sql)
        finally:
            await connection.close()

    return asyncio.run(_fetch())


async def _create_test_role(database_url: str) -> None:
    """Crée le rôle non-superuser et lui donne la main sur le schéma public."""
    connection = await asyncpg.connect(_raw_pg_url(database_url))
    try:
        try:
            await connection.execute(f"CREATE ROLE {TEST_ROLE} LOGIN")
        except asyncpg.DuplicateObjectError:
            pass  # rôle déjà présent sur ce cluster
        await connection.execute(f"GRANT ALL PRIVILEGES ON SCHEMA public TO {TEST_ROLE}")
        # Les tables créées plus tard (nouvelles phases) reçoivent les mêmes droits.
        await connection.execute(
            "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public"
            f" GRANT ALL PRIVILEGES ON TABLES TO {TEST_ROLE}"
        )
        await connection.execute(
            f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {TEST_ROLE}"
        )
    finally:
        await connection.close()


def _as_test_role(database_url: str) -> str:
    """Même base, mais connectée en tant que rôle non-superuser (la RLS s'applique)."""
    test_url = database_url.replace("://postgres:@", f"://{TEST_ROLE}:@", 1)
    if test_url == database_url:
        raise RuntimeError(f"utilisateur superuser introuvable dans {database_url}")
    return test_url


async def current_setting(session: AsyncSession, key: str) -> str | None:
    """Valeur d'un paramètre de session PostgreSQL (None si le paramètre n'est pas défini)."""
    result = await session.execute(text("SELECT current_setting(:key, true)"), {"key": key})
    value: object | None = result.scalar_one_or_none()
    return str(value) if value is not None else None


async def seed_organization_with_admin(
    session: AsyncSession, *, name: str, email: str
) -> tuple[uuid.UUID, uuid.UUID]:
    """Crée une organisation et son admin : la RLS refuse l'écriture sans tenant posé.

    Retourne (organization_id, user_id).
    """
    organization = await organizations_repository.create_organization(session, name=name)
    user = await users_repository.create_user(session, email=email, password_hash="hachage-factice")
    await set_tenant(session, user_id=user.id, organization_id=organization.id)
    await memberships_repository.create_membership(
        session,
        organization_id=organization.id,
        user_id=user.id,
        role=Role.ADMIN,
    )
    return organization.id, user.id


async def register_client(
    client: httpx.AsyncClient,
    *,
    email: str = "admin@example.com",
    password: str = "mot-de-passe-secret",
    organization_name: str = "Acme",
    siren: str | None = None,
) -> httpx.Response:
    """Inscription via l'API : le parcours standard des tests d'authentification."""
    payload: dict[str, str] = {
        "email": email,
        "password": password,
        "organization_name": organization_name,
    }
    if siren is not None:
        payload["siren"] = siren
    return await client.post(f"{API_PREFIX}/auth/register", json=payload)


def build_request(app: FastAPI, path: str = "/") -> Request:
    """Request ASGI minimale portant l'application : sert à tester les dépendances FastAPI."""
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "app": app,
        }
    )


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    """Base PostgreSQL réelle, isolée et jetable : créée une fois par session de tests."""
    datadir = Path(tempfile.mkdtemp(prefix="mirador-pg-"))
    # cleanup_mode="delete" : le cluster est supprimé à la fin (sinon chaque
    # session de tests laisse ~50 Mo dans %TEMP% et remplit le disque).
    server = pgserver.get_server(str(datadir), cleanup_mode="delete")
    try:
        # pgserver expose postgresql:// ; SQLAlchemy a besoin du dialecte +asyncpg.
        yield server.get_uri().replace("postgresql://", SQLALCHEMY_URL_PREFIX, 1)
    finally:
        server.cleanup()


@pytest.fixture(scope="session")
def migrated_test_database_url(test_database_url: str) -> str:
    """Base de test migrée, ouverte en rôle non-superuser (la RLS s'applique donc)."""
    upgrade_to_head(test_database_url)
    asyncio.run(_create_test_role(test_database_url))
    return _as_test_role(test_database_url)


@pytest.fixture
def alembic_test_database_url(test_database_url: str) -> Iterator[str]:
    """Base vierge par test : les allers-retours ne touchent jamais à la base partagée."""
    database_name = f"mirador_rt_{uuid.uuid4().hex[:12]}"
    create_test_database(test_database_url, database_name)
    try:
        yield _with_database(test_database_url, database_name)
    finally:
        drop_test_database(test_database_url, database_name)


@pytest.fixture(autouse=True)
async def clean_tables(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[None]:
    """Base vidée avant chaque test : les tests HTTP commitent, les autres rollback.

    Sans nettoyage, deux tests qui s'inscrivent avec le même e-mail entrent en
    conflit sur la contrainte d'unicité (piège rencontré en phase 2a).
    """
    async with session_factory() as session:
        await session.execute(
            text(
                "TRUNCATE users, organizations, memberships, module_permissions,"
                " invitations, audit_logs, sessions, auth_challenges, backup_codes,"
                " password_reset_tokens, metric_snapshots, legal_profiles,"
                " legal_identifiers CASCADE"
            )
        )
        await session.commit()
    yield


@pytest.fixture
def app(migrated_test_database_url: str) -> FastAPI:
    """Application branchée sur la base de test migrée."""
    return create_app(Settings(database_url=migrated_test_database_url))


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Client HTTP ASGI contre l'application sous test."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    # httpx ASGITransport ne déclenche pas le lifespan : on libère le pool nous-mêmes.
    await app.state.engine.dispose()


@pytest.fixture
async def session_factory(
    migrated_test_database_url: str,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Fabrique de sessions sur la base migrée (usage direct des repositories en test)."""
    engine = create_async_engine(migrated_test_database_url)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Session isolée : annulée en fin de test pour ne jamais contaminer les autres tests."""
    session = session_factory()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
