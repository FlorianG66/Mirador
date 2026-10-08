"""Fournisseur OpenID Connect Google : URL d'autorisation et échange du code.

Façade branchée sur `app.state.oidc_provider` (même schéma que `email_sender`) :
les tests substituent un fournisseur sans réseau, le fournisseur réel n'est
utilisé qu'environnement avec les identifiants Google renseignés.

Choix d'implémentation : l'échange du code se fait en HTTPS avec le
`client_secret`, puis le userinfo donne l'identité — pas de vérification locale
du JWT (ni de dépendance crypto), et Google reste la seule source de vérité
sur l'e-mail (voir docs/DECISIONS.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

import httpx

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_SCOPES = "openid email profile"
# Une réponse Google lente ne doit pas faire tourner la requête en dépendance.
OIDC_TIMEOUT_SECONDS = 10


class OidcProviderError(Exception):
    """Le fournisseur a refusé, mal répondu ou renvoyé un userinfo incomplet."""


@dataclass(frozen=True)
class OidcIdentity:
    """Identité confirmée par le fournisseur : sujet stable, e-mail vérifié, nom affiché."""

    subject: str
    email: str
    email_verified: bool
    name: str | None


class OidcProvider(Protocol):
    """Contrat minimal d'un fournisseur OIDC (implémenté par Google, simulé en test)."""

    def authorization_url(self, *, state: str, redirect_uri: str) -> str:
        """URL d'autorisation : porte l'état qui reviendra dans le callback."""
        ...

    async def exchange_code(self, *, code: str, redirect_uri: str) -> OidcIdentity:
        """Échange le code d'autorisation contre l'identité de l'utilisateur."""
        ...


def _required_text(payload: object, key: str) -> str:
    """Champ obligatoire d'une réponse JSON : absent ou vide, c'est un refus du fournisseur."""
    value = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(value, str) or not value:
        raise OidcProviderError(f"Champ « {key} » absent de la réponse Google.")
    return value


class GoogleOidcProvider:
    """Client OIDC Google (flux code + userinfo), sans état local."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not client_id:
            raise ValueError("google_client_id est requis pour la connexion Google")
        self._client_id = client_id
        self._client_secret = client_secret
        # Transport injectable : les tests utilisent httpx.MockTransport, sans réseau.
        self._transport = transport

    def authorization_url(self, *, state: str, redirect_uri: str) -> str:
        """Construit l'URL d'autorisation Google (les paramètres sont encodés par urlencode)."""
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": GOOGLE_SCOPES,
                "state": state,
            }
        )
        return f"{GOOGLE_AUTH_ENDPOINT}?{query}"

    async def exchange_code(self, *, code: str, redirect_uri: str) -> OidcIdentity:
        """Échange le code contre un jeton, puis interroge le userinfo.

        Toute erreur réseau, HTTP ou JSON devient `OidcProviderError` : le routeur
        y répond 502 sans exposer le détail (journalisé par le gestionnaire).
        """
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=OIDC_TIMEOUT_SECONDS
            ) as client:
                token_response = await client.post(
                    GOOGLE_TOKEN_ENDPOINT,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                )
                token_response.raise_for_status()
                access_token = _required_text(token_response.json(), "access_token")
                userinfo_response = await client.get(
                    GOOGLE_USERINFO_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                userinfo_response.raise_for_status()
                userinfo = userinfo_response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # OidcProviderError n'est ni une erreur HTTP ni ValueError : il sort tel quel.
            raise OidcProviderError(f"Échange OIDC impossible : {exc}") from exc
        # Un userinfo sans `email_verified` est traité comme non vérifié (défaut sûr).
        verified = userinfo.get("email_verified") if isinstance(userinfo, dict) else None
        name = userinfo.get("name") if isinstance(userinfo, dict) else None
        return OidcIdentity(
            subject=_required_text(userinfo, "sub"),
            email=_required_text(userinfo, "email"),
            email_verified=verified is True,
            name=name if isinstance(name, str) else None,
        )
