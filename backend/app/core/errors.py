"""Erreurs normalisées RFC 9457 (application/problem+json)."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.db import DatabaseUnavailableError
from app.services.errors import ServiceProblem
from app.services.oidc import OidcProviderError

# « app.core.errors » : se propage jusqu'au logger « app » configuré par configure_logging().
logger = logging.getLogger(__name__)

PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"
PROBLEM_TYPE_BLANK = "about:blank"


def _problem_response(
    request: Request,
    status_code: int,
    detail: str,
    *,
    errors: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Construit la réponse problem+json (RFC 9457 : type, title, status, detail, instance)."""
    body: dict[str, Any] = {
        "type": PROBLEM_TYPE_BLANK,
        "title": HTTPStatus(status_code).phrase,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
    }
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convertit une HTTPException (404, 405…) en problème RFC 9457."""
    assert isinstance(exc, StarletteHTTPException)
    detail = (
        exc.detail
        if isinstance(exc.detail, str)
        else json.dumps(jsonable_encoder(exc.detail), ensure_ascii=False)
    )
    return _problem_response(request, exc.status_code, detail, headers=dict(exc.headers or {}))


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convertit une erreur de validation Pydantic/FastAPI (422) en problème RFC 9457."""
    assert isinstance(exc, RequestValidationError)
    return _problem_response(
        request,
        422,
        "Les paramètres de la requête sont invalides.",
        errors=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Dernier recours (500) : problème RFC 9457 sans fuite de détails internes."""
    # exc_info construit explicitement : logger.exception() n'a pas de contexte except ici.
    logger.error(
        "Erreur non gérée sur %s",
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return _problem_response(request, 500, "Une erreur interne est survenue.")


async def database_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    """PostgreSQL injoignable (503)."""
    assert isinstance(exc, DatabaseUnavailableError)
    logger.warning("Base indisponible sur %s : %s", request.url.path, exc)
    return _problem_response(request, 503, "La base de données est momentanément indisponible.")


async def service_problem_handler(request: Request, exc: Exception) -> JSONResponse:
    """Refus métier d'un service (conflit, accès interdit...) déjà prêt à sérialiser."""
    assert isinstance(exc, ServiceProblem)
    return _problem_response(request, exc.status_code, exc.detail)


async def oidc_provider_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Échec du fournisseur Google (réseau, code refusé) : 502 sans fuite de détail.

    Le détail technique part au journal, jamais au client (ASVS L2) : le message
    affiché est figé côté backend, indépendant de ce que Google a répondu.
    """
    assert isinstance(exc, OidcProviderError)
    logger.warning("Fournisseur OIDC en échec sur %s : %s", request.url.path, exc)
    return _problem_response(request, 502, "Connexion Google impossible.")


def register_exception_handlers(app: FastAPI) -> None:
    """Branche tous les gestionnaires d'erreurs sur l'application."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(DatabaseUnavailableError, database_unavailable_handler)
    app.add_exception_handler(ServiceProblem, service_problem_handler)
    app.add_exception_handler(OidcProviderError, oidc_provider_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
