"""Tests de la couche base : version du serveur, base injoignable."""

from __future__ import annotations

import pytest

from app.core.db import DatabaseUnavailableError, get_database_version
from tests.conftest import UNREACHABLE_DATABASE_URL


async def test_get_database_version_returns_postgres_banner(test_database_url: str) -> None:
    version = await get_database_version(test_database_url)

    assert version.startswith("PostgreSQL")


async def test_get_database_version_raises_when_unreachable() -> None:
    with pytest.raises(DatabaseUnavailableError):
        await get_database_version(UNREACHABLE_DATABASE_URL)


def test_database_unavailable_error_message_is_explicit() -> None:
    error = DatabaseUnavailableError("connexion refusée sur 127.0.0.1:1")

    assert isinstance(error, RuntimeError)
    assert "127.0.0.1:1" in str(error)
