"""Tests du registre de connecteurs (SPEC §5.4)."""

import pytest

from app import connectors
from app.connectors import Connector
from app.connectors.mock import MockFinanceConnector
from app.models.enums import Module


def test_les_quatre_modules_ont_un_connecteur_registre() -> None:
    assert connectors.list_categories() == [
        Module.FINANCE,
        Module.PROJECTS,
        Module.SOCIAL,
        Module.WEB,
    ]


def test_get_class_par_provider() -> None:
    assert connectors.get_class("mock.finance") is MockFinanceConnector
    assert connectors.get_class("inconnu") is None


def test_make_instancie_avec_seed() -> None:
    connector = connectors.make("mock.finance", seed=42)
    assert isinstance(connector, Connector)
    assert connector.provider == "mock.finance"
    assert connector.seed == 42


def test_make_provider_inconnu_leve_key_error() -> None:
    with pytest.raises(KeyError):
        connectors.make("stripe.reel")
