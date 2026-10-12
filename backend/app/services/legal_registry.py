"""Service `LegalRegistry` : lecture des registres officiels d'identité légale.

Le MVP s'appuie sur l'API Recherche d'entreprises (service public « recherche-entreprises »,
gratuit et sans clé, qui agrège Sirene, le RNE et l'INPI), avec un repli prévu sur l'API
Sirene de l'INSEE (clé requise) — SPEC §3, §5.4. Deux règles gouvernent ce module :

- **Aucun appel réseau dans les tests.** Le client reçoit un `httpx.AsyncBaseTransport`
  injectable (même schéma que `GoogleOidcProvider`) ; la CI fournit un transport simulé et
  n'exécute jamais de requête réelle.
- **Cache, timeout et backoff** pour respecter la limite d'environ 7 requêtes/seconde du
  service public. Les valeurs et la forme exacte des réponses doivent être confirmées sur la
  documentation officielle avant la mise en production : le mapping ci-dessous est tolérant
  aux champs absents plutôt que de présumer une structure figée (AGENTS.md §2 : ne rien
  deviner). Un champ manquant devient `None`, jamais une valeur inventée.

Le modèle `LegalCompany` est la forme canonique **interne** (indépendante du fournisseur) ;
un fournisseur de repli (INSEE, puis d'autres pays) devra produire la même structure.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

import httpx

RECHERCHE_ENTREPRISES_ENDPOINT = "https://recherche-entreprises.api.gouv.fr/search"
LEGAL_REGISTRY_TIMEOUT_SECONDS = 10
# Le cache amortit la limite du service public (~7 req/s) entre deux rafraîchissements.
LEGAL_REGISTRY_CACHE_TTL_SECONDS = 24 * 3600
# Deux nouvelles tentatives suffisent à absorber un pic de débit passager.
LEGAL_REGISTRY_MAX_RETRIES = 2
# Plafond d'attente entre deux tentatives quand l'en-tête Retry-After est absent ou trop grand.
LEGAL_REGISTRY_MAX_BACKOFF_SECONDS = 5.0


class LegalRegistryError(Exception):
    """Le registre a refusé, mal répondu ou renvoyé une charge illisible."""


@dataclass(frozen=True)
class LegalLeader:
    """Dirigeant tel que publié au registre (données personnelles minimales)."""

    nom: str
    qualite: str | None = None


@dataclass(frozen=True)
class LegalCompany:
    """Fiche d'entreprise canonique, indépendante du registre qui l'a produite.

    Tous les champs sauf `siren` et `source` sont optionnels : les registres ouverts sont
    incomplets, et une entreprise « non diffusible » (`diffusable=False`) ne publie ni
    dirigeants ni adresse — ces champs restent `None` et la saisie manuelle prend le relais.
    """

    siren: str
    source: str
    diffusable: bool = True
    siret_siege: str | None = None
    raison_sociale: str | None = None
    nom_commercial: str | None = None
    forme_juridique: str | None = None
    date_creation: date | None = None
    code_naf: str | None = None
    libelle_naf: str | None = None
    adresse: str | None = None
    tranche_effectif: str | None = None
    dirigeants: tuple[LegalLeader, ...] = field(default_factory=tuple)


class LegalRegistry(Protocol):
    """Contrat minimal d'un registre d'identité légale (implémenté par l'API publique)."""

    async def fetch_by_siren(self, siren: str) -> LegalCompany | None:
        """Renvoie la fiche d'une entreprise, ou `None` si le SIREN est inconnu."""
        ...


def _text(value: object) -> str | None:
    """Chaîne non vide, sinon `None` (les registres renvoient souvent `null` ou `""`)."""
    return value if isinstance(value, str) and value else None


def _mapping(value: object) -> dict[str, Any]:
    """Sous-objet JSON, sinon dictionnaire vide : le parsing reste tolérant."""
    return value if isinstance(value, dict) else {}


def _parse_date(value: object) -> date | None:
    """Date ISO `AAAA-MM-JJ` ; toute autre forme est ignorée plutôt que devinée."""
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _is_diffusable(result: dict[str, Any]) -> bool:
    """Détermine si l'entreprise est diffusible (sinon dirigeants/adresse à masquer).

    Le service public signale une entreprise non diffusible par ``statut_diffusion == "N"``
    ou ``diffusable_commercialement == False`` selon la source ; en l'absence d'indice, on
    suppose diffusible (comportement par défaut du registre public).
    """
    if _text(result.get("statut_diffusion")) == "N":
        return False
    return result.get("diffusable_commercialement") is not False


def parse_recherche_entreprise(result: dict[str, Any]) -> LegalCompany | None:
    """Traduit un résultat de l'API Recherche d'entreprises en `LegalCompany`.

    Mapping à confirmer sur la documentation officielle : chaque champ est lu de façon
    tolérante (absent = `None`). Un résultat sans SIREN exploitable est écarté (`None`).
    Les dirigeants d'une entreprise non diffusible sont volontairement omis.
    """
    siren = _text(result.get("siren"))
    if siren is None:
        return None
    siege = _mapping(result.get("siege"))
    diffusable = _is_diffusable(result)
    leaders: tuple[LegalLeader, ...] = ()
    if diffusable:
        for entry in result.get("dirigeants") or []:
            if not isinstance(entry, dict):
                continue
            nom = _text(entry.get("nom")) or _text(entry.get("prenoms"))
            if nom is None:
                continue
            leaders = (
                *leaders,
                LegalLeader(nom=nom, qualite=_text(entry.get("qualite"))),
            )
    return LegalCompany(
        siren=siren,
        source="registry",
        diffusable=diffusable,
        siret_siege=_text(siege.get("siret")),
        raison_sociale=_text(result.get("nom_raison_sociale")) or _text(result.get("nom_complet")),
        nom_commercial=_text(siege.get("nom_commercial")) or _text(result.get("nom_commercial")),
        forme_juridique=_text(result.get("nature_juridique")),
        date_creation=_parse_date(result.get("date_creation")),
        code_naf=_text(siege.get("activite_principale")),
        libelle_naf=_text(siege.get("libelle_activite_principale")),
        adresse=_text(siege.get("adresse")) if diffusable else None,
        tranche_effectif=_text(siege.get("tranche_effectif_salarie")),
        dirigeants=leaders,
    )


class RechercheEntreprisesRegistry:
    """Client de l'API Recherche d'entreprises, avec cache mémoire et repli par retentatives.

    `transport` est injectable (`httpx.MockTransport` en test) : sans lui, le client créerait
    une connexion réelle, ce que la CI ne doit jamais faire.
    """

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        endpoint: str = RECHERCHE_ENTREPRISES_ENDPOINT,
        timeout_seconds: float = LEGAL_REGISTRY_TIMEOUT_SECONDS,
        cache_ttl_seconds: float = LEGAL_REGISTRY_CACHE_TTL_SECONDS,
        max_retries: int = LEGAL_REGISTRY_MAX_RETRIES,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._transport = transport
        self._endpoint = endpoint
        self._timeout = timeout_seconds
        self._cache_ttl = cache_ttl_seconds
        self._max_retries = max_retries
        # `sleep` injectable : les tests absorbent le backoff sans attendre réellement.
        self._sleep = sleep
        self._cache: dict[str, tuple[float, LegalCompany | None]] = {}

    async def fetch_by_siren(self, siren: str) -> LegalCompany | None:
        """Renvoie la fiche du SIREN, servie depuis le cache tant qu'il est chaud."""
        found, cached = self._from_cache(siren)
        if found:
            return cached
        company = await self._fetch_remote(siren)
        self._cache[siren] = (time.monotonic() + self._cache_ttl, company)
        return company

    def _from_cache(self, siren: str) -> tuple[bool, LegalCompany | None]:
        """Lit le cache : `(True, fiche)` s'il est chaud, `(False, None)` sinon.

        Le tuple distingue « absent du cache » de « SIREN inconnu mémorisé » (valeur
        `None` légitime) sans recourir à une sentinelle de type `object`.
        """
        entry = self._cache.get(siren)
        if entry is None:
            return (False, None)
        expires_at, company = entry
        if time.monotonic() >= expires_at:
            del self._cache[siren]
            return (False, None)
        return (True, company)

    async def _fetch_remote(self, siren: str) -> LegalCompany | None:
        """Appelle le service public, en retentant sur 429/5xx avec backoff borné."""
        attempt = 0
        while True:
            try:
                response = await self._get(siren)
            except httpx.HTTPError as exc:
                raise LegalRegistryError(f"Registre injoignable : {exc}") from exc
            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self._max_retries:
                    raise LegalRegistryError(
                        f"Registre indisponible (HTTP {response.status_code})."
                    )
                await self._sleep(self._backoff_seconds(response, attempt))
                attempt += 1
                continue
            if response.status_code != 200:
                raise LegalRegistryError(f"Registre a répondu HTTP {response.status_code}.")
            return self._parse_payload(response)

    async def _get(self, siren: str) -> httpx.Response:
        async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
            return await client.get(self._endpoint, params={"q": siren})

    def _parse_payload(self, response: httpx.Response) -> LegalCompany | None:
        try:
            payload = response.json()
        except ValueError as exc:
            raise LegalRegistryError("Réponse du registre illisible (JSON invalide).") from exc
        results = _mapping(payload).get("results")
        if not isinstance(results, list) or not results:
            return None  # SIREN inconnu : le registre répond une liste vide, pas une erreur.
        first = results[0]
        if not isinstance(first, dict):
            raise LegalRegistryError("Résultat du registre inattendu.")
        return parse_recherche_entreprise(first)

    @staticmethod
    def _backoff_seconds(response: httpx.Response, attempt: int) -> float:
        """Attente entre deux tentatives : en-tête Retry-After, sinon backoff exponentiel borné."""
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return min(float(retry_after), LEGAL_REGISTRY_MAX_BACKOFF_SECONDS)
            except ValueError:
                pass
        return min(2.0**attempt, LEGAL_REGISTRY_MAX_BACKOFF_SECONDS)
