"""Construction de l'application FastAPI (assemblage des routes, erreurs, logging)."""

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.constants import API_PREFIX, API_VERSION, PROJECT_NAME
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.routers.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Crée l'application ; settings=None charge la configuration de l'environnement."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    app = FastAPI(
        title=PROJECT_NAME,
        version=API_VERSION,
        description=f"API {PROJECT_NAME} — dashboard d'entreprise",
    )
    app.state.settings = resolved_settings
    app.include_router(health_router, prefix=API_PREFIX)
    register_exception_handlers(app)
    return app
