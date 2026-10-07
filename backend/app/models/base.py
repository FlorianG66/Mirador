"""Déclarative de base : classe mère de toutes les tables (metadata partagée)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Metadata commune — cible d'autogénération d'Alembic."""
