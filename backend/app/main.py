"""Construction de l'application FastAPI (assemblage des routes, erreurs, logging)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.constants import API_PREFIX, API_VERSION, PROJECT_NAME
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import SecurityMiddleware
from app.core.rate_limit import RateLimiter
from app.routers.auth import router as auth_router
from app.routers.goals import router as goals_router
from app.routers.google import router as google_router
from app.routers.health import router as health_router
from app.routers.invitations import accept_router as invitation_accept_router
from app.routers.invitations import router as invitations_router
from app.routers.legal import router as legal_router
from app.routers.metrics import router as metrics_router
from app.routers.password import router as password_router
from app.routers.pulse import router as pulse_router
from app.routers.team import router as team_router
from app.routers.two_factor import router as two_factor_router
from app.services.emails import LogEmailSender
from app.services.legal_registry import RechercheEntreprisesRegistry
from app.services.oidc import GoogleOidcProvider
from app.workers.scheduler import JobScheduler
from app.workers.sync import sync_all_organizations


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Démarre le worker de synchro (phase 4c), puis libère le pool à l'arrêt.

    Le planificateur tourne seulement si `sync_interval_minutes > 0` (0 désactive,
    choisi dans les tests). Les tests httpx ne déclenchent pas le lifespan :
    ils libèrent le pool eux-mêmes.
    """
    settings: Settings = application.state.settings
    scheduler: JobScheduler | None = None
    if settings.sync_interval_minutes > 0:
        scheduler = JobScheduler(
            lambda: sync_all_organizations(application.state.session_factory),
            interval_seconds=settings.sync_interval_minutes * 60,
            name="sync",
        )
        await scheduler.start()
    yield
    if scheduler is not None:
        await scheduler.stop()
    engine: AsyncEngine = application.state.engine
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Crée l'application ; settings=None charge la configuration de l'environnement."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    app = FastAPI(
        title=PROJECT_NAME,
        version=API_VERSION,
        description=f"API {PROJECT_NAME} — dashboard d'entreprise",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    # En-têtes de sécurité + CSRF : une couche unique, au-dessus de toutes les routes.
    app.add_middleware(SecurityMiddleware, settings=resolved_settings)
    # Compteur de tentatives d'authentification, isolé par application (donc par test).
    app.state.rate_limiter = RateLimiter()
    # Envoi d'e-mails : journalisation en développement, SMTP en phase 11.
    app.state.email_sender = LogEmailSender()
    # Registre d'identité légale (SPEC §3) : service public sans clé ; les tests
    # remplacent cette instance par un registre factice sur `app.state`.
    app.state.legal_registry = RechercheEntreprisesRegistry()
    # Connexion Google : fournisseur absent (routes en 404) tant que les
    # identifiants ne sont pas renseignés dans l'environnement.
    app.state.oidc_provider = (
        GoogleOidcProvider(
            client_id=resolved_settings.google_client_id,
            client_secret=resolved_settings.google_client_secret,
        )
        if resolved_settings.google_client_id
        else None
    )
    engine = create_async_engine(resolved_settings.database_url)
    app.state.engine = engine
    # Une fabrique partagée : une session (donc une transaction) par requête.
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(google_router, prefix=API_PREFIX)
    app.include_router(two_factor_router, prefix=API_PREFIX)
    app.include_router(password_router, prefix=API_PREFIX)
    app.include_router(invitations_router, prefix=API_PREFIX)
    app.include_router(invitation_accept_router, prefix=API_PREFIX)
    app.include_router(team_router, prefix=API_PREFIX)
    app.include_router(metrics_router, prefix=API_PREFIX)
    app.include_router(goals_router, prefix=API_PREFIX)
    app.include_router(pulse_router, prefix=API_PREFIX)
    app.include_router(legal_router, prefix=API_PREFIX)
    app.include_router(health_router, prefix=API_PREFIX)
    register_exception_handlers(app)
    return app
