"""Connecteurs de données (SPEC §5.4) : l'interface `Connector`, le registre des
providers et les connecteurs de démonstration (mocks déterministes par seed).

L'import de `app.connectors` enregistre les connecteurs du dépôt dans le registre.
"""

from app.connectors.base import Connector, ConnectorHealth
from app.connectors.finance import MockFinanceConnector, build_finance_series
from app.connectors.mock import (
    MOCK_CONNECTORS,
    MockConnector,
    MockProjectsConnector,
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
from app.connectors.social import MockSocialConnector, build_social_series
from app.connectors.web import MockWebConnector, build_web_series

ALL_CONNECTORS: tuple[type[Connector], ...] = (
    MockFinanceConnector,
    MockWebConnector,
    MockSocialConnector,
    *MOCK_CONNECTORS,
)
for _connector_cls in ALL_CONNECTORS:
    register(_connector_cls)

__all__ = [
    "Connector",
    "ConnectorHealth",
    "MockConnector",
    "MockFinanceConnector",
    "MockWebConnector",
    "MockSocialConnector",
    "MockProjectsConnector",
    "build_finance_series",
    "build_web_series",
    "build_social_series",
    "get_class",
    "list_categories",
    "list_connectors",
    "make",
    "make_all",
    "register",
    "reset",
]
