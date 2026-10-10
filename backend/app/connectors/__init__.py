"""Connecteurs de données (SPEC §5.4) : l'interface `Connector`, le registre des
providers et les connecteurs de démonstration (mocks déterministes par seed).

L'import de `app.connectors` enregistre les connecteurs du dépôt dans le registre.
"""

from app.connectors.base import Connector, ConnectorHealth
from app.connectors.mock import (
    MOCK_CONNECTORS,
    MockConnector,
    MockFinanceConnector,
    MockProjectsConnector,
    MockSocialConnector,
    MockWebConnector,
)
from app.connectors.registry import (
    get_class,
    list_categories,
    list_connectors,
    make,
    make_all,
    register,
    reset,
)

for _connector_cls in MOCK_CONNECTORS:
    register(_connector_cls)

__all__ = [
    "Connector",
    "ConnectorHealth",
    "MockConnector",
    "MockFinanceConnector",
    "MockWebConnector",
    "MockSocialConnector",
    "MockProjectsConnector",
    "get_class",
    "list_categories",
    "list_connectors",
    "make",
    "make_all",
    "register",
    "reset",
]
