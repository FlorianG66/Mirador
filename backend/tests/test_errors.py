"""Tests des erreurs normalisées RFC 9457 (application/problem+json)."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus

import httpx
import pytest
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

import app.core.errors as errors_module
from app.core.errors import (
    PROBLEM_JSON_MEDIA_TYPE,
    unhandled_exception_handler,
    validation_exception_handler,
)


def _request(path: str = "/api/v1/health") -> Request:
    """Construit une Request Starlette minimaliste pour tester les handlers unitairement."""
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
        }
    )


def _assert_is_problem(response_content: bytes, expected_status: int) -> dict[str, object]:
    body = json.loads(response_content)
    assert body["type"] == "about:blank"
    assert body["status"] == expected_status
    assert body["title"] == HTTPStatus(expected_status).phrase
    return body


async def test_unknown_route_returns_problem_json(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/ce-n-existe-pas")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_JSON_MEDIA_TYPE)
    body = _assert_is_problem(response.content, 404)
    assert body["instance"] == "/api/v1/ce-n-existe-pas"
    assert body["detail"]


async def test_wrong_method_returns_problem_json(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.headers["content-type"].startswith(PROBLEM_JSON_MEDIA_TYPE)
    _assert_is_problem(response.content, 405)


async def test_validation_error_returns_problem_with_field_errors() -> None:
    error = {
        "type": "missing",
        "loc": ("query", "q"),
        "msg": "Field required",
        "input": {},
    }
    exc = RequestValidationError(errors=[error])

    response = await validation_exception_handler(_request(), exc)

    assert response.status_code == 422
    assert response.media_type == PROBLEM_JSON_MEDIA_TYPE
    body = _assert_is_problem(response.body, 422)
    assert body["errors"]
    assert body["detail"]


async def test_unhandled_exception_returns_problem_without_leaking_details() -> None:
    exc = ValueError("mot-de-passe=le-secret")

    response = await unhandled_exception_handler(_request(), exc)

    assert response.status_code == 500
    assert response.media_type == PROBLEM_JSON_MEDIA_TYPE
    body = _assert_is_problem(response.body, 500)
    assert "le-secret" not in json.dumps(body)


class _RecordingHandler(logging.Handler):
    """Handler minimaliste : mémorise les records pour les assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


async def test_unhandled_exception_is_logged_with_traceback() -> None:
    # Le vrai logger du module (« app.core.errors »), pas un nom supposé.
    error_logger = logging.getLogger(errors_module.__name__)
    recorder = _RecordingHandler()
    error_logger.addHandler(recorder)
    error_logger.setLevel(logging.DEBUG)
    try:
        await unhandled_exception_handler(_request(), ValueError("boom"))
    finally:
        error_logger.removeHandler(recorder)

    assert recorder.records, "l'erreur 500 doit être journalisée"
    assert recorder.records[0].exc_info is not None
    assert isinstance(recorder.records[0].exc_info[1], ValueError)


async def test_database_unavailable_handler_returns_503_problem() -> None:
    """Réutilisable par n'importe quelle couche qui perd la base."""
    from app.core.db import DatabaseUnavailableError
    from app.core.errors import database_unavailable_handler

    response = await database_unavailable_handler(
        _request("/api/v1/health/db"), DatabaseUnavailableError("base injoignable")
    )

    assert response.status_code == 503
    assert response.media_type == PROBLEM_JSON_MEDIA_TYPE
    _assert_is_problem(response.body, 503)


@pytest.mark.parametrize("status", [404, 405, 500])
async def test_problem_uses_http_reason_phrase_as_title(status: int) -> None:
    """Le titre du problème reprend la phrase HTTP standard (RFC 9457)."""
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from app.core.errors import http_exception_handler

    response = await http_exception_handler(
        _request(), StarletteHTTPException(status_code=status, detail="détail")
    )

    assert response.status_code == status
    body = _assert_is_problem(response.body, status)
    assert body["detail"] == "détail"
