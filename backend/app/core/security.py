"""Primitives de sécurité : hachage Argon2id et jetons opaques (phase 2b).

Les jetons d'accès et de rafraîchissement sont aléatoires : seul leur hachage
SHA-256 vit en base, pour qu'une fuite de la table `sessions` ne permette pas
de rejouer un jeton.
"""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Durées de vie des cookies (AGENTS.md §5 : session courte, rotation du rafraîchi).
ACCESS_TOKEN_TTL_SECONDS = 900
REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 3600

# Recommandations OWASP pour Argon2id (v1.3) : mémoire 19 Mo, 2 itérations, 1 fil.
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


def hash_password(password: str) -> str:
    """Hache un mot de passe avec Argon2id (salé par la librairie, jamais stocké en clair)."""
    return _hasher.hash(password)


def verify_password(password: str, digest: str) -> bool:
    """Vérifie un mot de passe contre son hachage : False pour tout hachage invalide."""
    try:
        return _hasher.verify(digest, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def generate_token() -> str:
    """Génère un jeton opaque URL-safe (32 octets d'entropie, ~43 caractères)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Empreinte SHA-256 d'un jeton : la seule forme conservée en base."""
    return hashlib.sha256(token.encode()).hexdigest()
