"""Schémas des réponses de santé (health)."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Réponse de GET /health."""

    status: Literal["ok"]
    service: str
    version: str


class DatabaseDetails(BaseModel):
    """État détaillé de la base."""

    status: Literal["ok"]
    server_version: str


class DatabaseHealthResponse(BaseModel):
    """Réponse de GET /health/db."""

    status: Literal["ok"]
    database: DatabaseDetails
