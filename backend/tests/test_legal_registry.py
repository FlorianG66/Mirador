"""Service `LegalRegistry` et validations légales (5e-a) : aucun appel réseau réel.

Le client reçoit un `httpx.MockTransport` : les réponses des registres sont simulées,
comme l'exige la ROADMAP pour la 5e (« jamais d'appel réel en CI »).
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.core.siren import (
    french_vat_key,
    french_vat_number,
    is_valid_siren,
    is_valid_siret,
)
from app.services.legal_registry import (
    LegalRegistryError,
    RechercheEntreprisesRegistry,
    parse_recherche_entreprise,
)

# Exemples figés, vérifiés une fois pour toutes (pas de calcul circulaire).
VALID_SIREN = "732829320"
VALID_SIRET = "73282932000017"


async def _no_sleep(_seconds: float) -> None:
    """Absorbe le backoff sans attendre réellement entre deux tentatives."""


def _registry(handler: httpx.MockTransport) -> RechercheEntreprisesRegistry:
    return RechercheEntreprisesRegistry(
        transport=httpx.MockTransport(handler),
        cache_ttl_seconds=1000,
        sleep=_no_sleep,
    )


def _full_result() -> dict[str, object]:
    return {
        "siren": VALID_SIREN,
        "nom_raison_sociale": "EXEMPLE INDUSTRIE",
        "nature_juridique": "5499",
        "date_creation": "2001-03-15",
        "siege": {
            "siret": VALID_SIRET,
            "nom_commercial": "Exemple & Cie",
            "adresse": "12 rue de l'Exemple 75001 Paris",
            "activite_principale": "25.62B",
            "tranche_effectif_salarie": "20",
        },
        "dirigeants": [
            {"nom": "MARTIN", "prenoms": "Camille", "qualite": "Présidente"},
            {"nom": "DUPONT", "qualite": "Directeur général"},
        ],
    }


# --- Validations SIREN / SIRET / TVA ------------------------------------------------


def test_siren_luhn_accepts_a_valid_number() -> None:
    assert is_valid_siren(VALID_SIREN) is True


def test_siren_luhn_rejects_a_bad_check_digit() -> None:
    assert is_valid_siren("732829321") is False


def test_siren_luhn_rejects_wrong_length_or_non_digits() -> None:
    assert is_valid_siren("12345678") is False
    assert is_valid_siren("12345678A") is False


def test_siret_luhn_accepts_a_valid_number() -> None:
    assert is_valid_siret(VALID_SIRET) is True


def test_siret_luhn_rejects_a_bad_check_digit() -> None:
    assert is_valid_siret("73282932000010") is False


def test_french_vat_number_matches_the_official_formula() -> None:
    # key = (12 + 3 * (SIREN mod 97)) mod 97 ; 732829320 mod 97 = 43 -> clé 44
    assert french_vat_key(VALID_SIREN) == "44"
    assert french_vat_number(VALID_SIREN) == "FR44732829320"


def test_french_vat_key_refuses_an_invalid_siren() -> None:
    with pytest.raises(ValueError):
        french_vat_key("123")


# --- Client du registre -------------------------------------------------------------


async def test_fetch_by_siren_parses_a_full_result() -> None:
    registry = _registry(lambda request: httpx.Response(200, json={"results": [_full_result()]}))
    company = await registry.fetch_by_siren(VALID_SIREN)
    assert company is not None
    assert company.siren == VALID_SIREN
    assert company.source == "registry"
    assert company.diffusable is True
    assert company.siret_siege == VALID_SIRET
    assert company.raison_sociale == "EXEMPLE INDUSTRIE"
    assert company.nom_commercial == "Exemple & Cie"
    assert company.forme_juridique == "5499"
    assert company.date_creation == date(2001, 3, 15)
    assert company.code_naf == "25.62B"
    assert company.adresse == "12 rue de l'Exemple 75001 Paris"
    assert company.tranche_effectif == "20"
    assert [leader.nom for leader in company.dirigeants] == ["MARTIN", "DUPONT"]
    assert company.dirigeants[0].qualite == "Présidente"


async def test_fetch_by_siren_returns_none_for_an_unknown_siren() -> None:
    registry = _registry(lambda request: httpx.Response(200, json={"results": []}))
    assert await registry.fetch_by_siren("000000000") is None


async def test_fetch_by_siren_caches_the_result() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"results": [_full_result()]})

    registry = _registry(handler)
    first = await registry.fetch_by_siren(VALID_SIREN)
    second = await registry.fetch_by_siren(VALID_SIREN)
    assert first == second
    assert len(calls) == 1  # la seconde lecture vient du cache


async def test_fetch_by_siren_masks_directors_of_a_non_diffusable_company() -> None:
    result = _full_result()
    result["statut_diffusion"] = "N"
    registry = _registry(lambda request: httpx.Response(200, json={"results": [result]}))
    company = await registry.fetch_by_siren(VALID_SIREN)
    assert company is not None
    assert company.diffusable is False
    assert company.dirigeants == ()
    assert company.adresse is None
    # Les informations non personnelles restent disponibles.
    assert company.raison_sociale == "EXEMPLE INDUSTRIE"


async def test_fetch_by_siren_tolerates_missing_optional_fields() -> None:
    registry = _registry(
        lambda request: httpx.Response(200, json={"results": [{"siren": VALID_SIREN}]})
    )
    company = await registry.fetch_by_siren(VALID_SIREN)
    assert company is not None
    assert company.raison_sociale is None
    assert company.date_creation is None
    assert company.dirigeants == ()


async def test_fetch_by_siren_retries_on_rate_limit_then_succeeds() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"results": [_full_result()]})

    registry = _registry(handler)
    company = await registry.fetch_by_siren(VALID_SIREN)
    assert company is not None
    assert len(calls) == 2


async def test_fetch_by_siren_gives_up_after_repeated_server_errors() -> None:
    registry = _registry(lambda request: httpx.Response(503))
    with pytest.raises(LegalRegistryError):
        await registry.fetch_by_siren(VALID_SIREN)


async def test_fetch_by_siren_fails_on_a_definitive_client_error() -> None:
    registry = _registry(lambda request: httpx.Response(400))
    with pytest.raises(LegalRegistryError):
        await registry.fetch_by_siren(VALID_SIREN)


async def test_fetch_by_siren_fails_on_invalid_json() -> None:
    registry = _registry(lambda request: httpx.Response(200, content=b"not-json"))
    with pytest.raises(LegalRegistryError):
        await registry.fetch_by_siren(VALID_SIREN)


async def test_fetch_by_siren_wraps_network_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("réseau indisponible")

    registry = _registry(handler)
    with pytest.raises(LegalRegistryError):
        await registry.fetch_by_siren(VALID_SIREN)


def test_parse_recherche_entreprise_ignores_a_result_without_siren() -> None:
    assert parse_recherche_entreprise({"nom_complet": "Sans SIREN"}) is None
