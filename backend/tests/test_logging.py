"""Tests du logging structuré : niveau, format JSON, idempotence."""

from __future__ import annotations

import json
import logging

from app.core.logging import APP_LOGGER_NAME, JsonFormatter, configure_logging


def _record(
    message: str = "message de test",
    level: int = logging.INFO,
    exc_info: tuple[type[BaseException], BaseException, object] | None = None,
) -> logging.LogRecord:
    return logging.LogRecord(
        name="mirador.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,  # type: ignore[arg-type]
    )


def test_json_formatter_emits_one_json_object_with_core_fields() -> None:
    output = JsonFormatter().format(_record())

    data = json.loads(output)
    assert data["level"] == "INFO"
    assert data["logger"] == "mirador.test"
    assert data["message"] == "message de test"
    assert data["timestamp"]  # horodatage ISO présent


def test_json_formatter_includes_traceback_on_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = _record(exc_info=sys.exc_info())

    data = json.loads(JsonFormatter().format(record))

    assert "ValueError: boom" in data["exc_info"]


def _app_handlers() -> list[logging.Handler]:
    """Handlers appartenant à Mirador (pytest injecte aussi ses propres handlers de capture)."""
    return [
        handler
        for handler in logging.getLogger(APP_LOGGER_NAME).handlers
        if isinstance(handler.formatter, JsonFormatter)
    ]


def test_configure_logging_sets_level_and_adds_single_handler() -> None:
    configure_logging("DEBUG")

    app_logger = logging.getLogger(APP_LOGGER_NAME)
    assert app_logger.level == logging.DEBUG
    handlers = _app_handlers()
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.StreamHandler)


def test_configure_logging_is_idempotent() -> None:
    """Appelé à plusieurs reprises (tests, workers) : jamais de handlers dupliqués."""
    configure_logging("INFO")
    configure_logging("INFO")

    assert len(_app_handlers()) == 1


def test_application_log_records_reach_the_app_logger() -> None:
    """Un module applicatif (app.core.errors…) propage bien jusqu'au handler structuré."""
    configure_logging("DEBUG")
    app_logger = logging.getLogger(APP_LOGGER_NAME)

    captured: list[str] = []
    capture = logging.Handler()
    capture.emit = lambda record: captured.append(record.getMessage())  # type: ignore[method-assign]
    app_logger.addHandler(capture)
    try:
        logging.getLogger("app.core.errors").error("une erreur métier")
    finally:
        app_logger.removeHandler(capture)

    assert captured == ["une erreur métier"]
