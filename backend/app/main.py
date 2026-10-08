"""Construction de l'application FastAPI (assemblage des routes, erreurs, logging)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.constants import API_PREFIX, API_VERSION, PROJECT_NAME
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.routers.health import router as health_router


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Libère le pool de connexions à l'arrêt (le client de test le fait lui-même)."""
    yield
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
    engine = create_async_engine(resolved_settings.database_url)
    app.state.engine = engine
    # Une fabrique partagée : une session (donc une transaction) par requête.
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.include_router(health_router, prefix=API_PREFIX)
    register_exception_handlers(app)
    return app
