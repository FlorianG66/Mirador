"""Routes de santé : vivacité de l'API et état de la base."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings
from app.core.constants import API_SERVICE, API_VERSION
from app.core.db import get_database_version
from app.core.deps import get_request_settings
from app.schemas.health import DatabaseDetails, DatabaseHealthResponse, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Vivacité : l'API répond, sans dépendre de la base."""
    return HealthResponse(status="ok", service=API_SERVICE, version=API_VERSION)


@router.get("/health/db", response_model=DatabaseHealthResponse)
async def get_database_health(
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> DatabaseHealthResponse:
    """État de la base : 200 si PostgreSQL répond, 503 sinon."""
    version = await get_database_version(settings.database_url)
    return DatabaseHealthResponse(
        status="ok",
        database=DatabaseDetails(status="ok", server_version=version),
    )
