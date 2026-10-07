"""Logging structuré : un objet JSON par ligne, niveau configurable."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

# Tous les modules applicatifs vivent sous « app » : ce logger racine capte leurs records.
APP_LOGGER_NAME = "app"


class JsonFormatter(logging.Formatter):
    """Formate un LogRecord en une ligne JSON exploitable par un collecteur de logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    """Configure le logger applicatif (idempotent : n'ajoute jamais deux handlers)."""
    app_logger = logging.getLogger(APP_LOGGER_NAME)
    app_logger.setLevel(level)
    # N'ajoute le handler que s'il manque : rappeler configure_logging ne duplique rien.
    if not any(isinstance(handler.formatter, JsonFormatter) for handler in app_logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        app_logger.addHandler(handler)
    # uvicorn journalise déjà via la racine : pas de doublon.
    app_logger.propagate = False
