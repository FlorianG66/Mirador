"""Registre des connecteurs disponibles (SPEC §5.4).

Le registre associe un `provider` à une classe de connecteur : l'application ne
connaît jamais les connecteurs en dur, elle interroge le registre par provider
ou par catégorie. Une instance est ensuite créée, éventuellement avec un seed
pour la démo.
"""

from __future__ import annotations

from app.connectors.base import Connector
from app.models.enums import Module

_connector_classes: dict[str, type[Connector]] = {}


def register(cls: type[Connector]) -> None:
    """Enregistre une classe de connecteur sous son attribut `provider`."""
    _connector_classes[cls.provider] = cls


def get_class(provider: str) -> type[Connector] | None:
    """Classe de connecteur du provider donné, ou `None` si inconnu."""
    return _connector_classes.get(provider)


def list_categories() -> list[Module]:
    """Catégories (modules) pour lesquelles au moins un connecteur est enregistré."""
    return sorted({cls.category for cls in _connector_classes.values()}, key=lambda m: m.value)


def list_connectors(category: Module | None = None) -> list[str]:
    """Providers enregistrés, optionnellement filtrés par catégorie."""
    return sorted(
        provider
        for provider, cls in _connector_classes.items()
        if category is None or cls.category == category
    )


def make(provider: str, seed: int | None = None) -> Connector:
    """Instancie le connecteur du provider ; positionne le seed pour les mocks."""
    cls = get_class(provider)
    if cls is None:
        raise KeyError(f"Connecteur inconnu : « {provider} »")
    return cls(seed)


def reset() -> None:
    """Vide le registre (utile aux tests qui réenregistrent des connecteurs)."""
    _connector_classes.clear()
