"""Service A2F : activation/désactivation TOTP et codes de secours (phase 2c).

Le secret TOTP est régénéré à chaque activation : réactiver remplace le secret
visible par l'utilisateur et révoque les anciens codes de secours. Vérifier le
second facteur ne consomme rien pour le TOTP, mais consomme un code de secours.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BACKUP_CODE_COUNT
from app.core.security import hash_token, verify_password
from app.core.totp import TOTP_WINDOW_STEPS, generate_totp_secret, otpauth_url, verify_totp
from app.models.user import User
from app.repositories import two_factor as two_factor_repository

# Alphabet sans caractères ambigus (pas de 0/O ni 1/I) : code lisible sur papier.
_BACKUP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_BACKUP_CODE_LENGTH = 8


@dataclass(frozen=True)
class TotpSetup:
    """Ce que l'activation renvoie : secret à afficher et codes de secours à copier."""

    secret: str
    otpauth_url: str
    backup_codes: list[str]


class WrongCurrentPassword(Exception):
    """Le mot de passe courant ne correspond pas : opération refusée."""


def _new_backup_codes() -> list[str]:
    """Émet des codes haute entropie (40 bits) : stockés hachés, jamais en clair."""
    return [
        "".join(secrets.choice(_BACKUP_ALPHABET) for _ in range(_BACKUP_CODE_LENGTH))
        for _ in range(BACKUP_CODE_COUNT)
    ]


async def enable(session: AsyncSession, *, user: User, current_password: str) -> TotpSetup:
    """Active le TOTP et réémet les codes de secours après vérification du premier facteur."""
    if not verify_password(current_password, user.password_hash or ""):
        raise WrongCurrentPassword
    secret = generate_totp_secret()
    user.totp_secret = secret
    user.totp_enabled_at = datetime.now(UTC)
    await two_factor_repository.delete_backup_codes_for_user(session, user_id=user.id)
    backup_codes = _new_backup_codes()
    await two_factor_repository.add_backup_codes(
        session,
        user_id=user.id,
        code_hashes=[hash_token(code) for code in backup_codes],
    )
    await session.flush()
    return TotpSetup(
        secret=secret,
        otpauth_url=otpauth_url(secret, user.email),
        backup_codes=backup_codes,
    )


async def disable(session: AsyncSession, *, user: User, current_password: str) -> None:
    """Désactive le TOTP et révoque tous les codes de secours restants."""
    if not verify_password(current_password, user.password_hash or ""):
        raise WrongCurrentPassword
    user.totp_secret = None
    user.totp_enabled_at = None
    await two_factor_repository.delete_backup_codes_for_user(session, user_id=user.id)
    await session.flush()


def accepts_totp(user: User, code: str) -> bool:
    """Vrai si `code` est un TOTP valide pour ce compte (aucune consommation)."""
    if user.totp_enabled_at is None or not user.totp_secret:
        return False
    return verify_totp(user.totp_secret, code, window=TOTP_WINDOW_STEPS)


async def consume_backup_code(session: AsyncSession, *, code_hash: str) -> bool:
    """Consomme un code de secours inutilisé ; False s'il est inconnu ou déjà usé."""
    row = await two_factor_repository.get_backup_code_by_hash(session, code_hash)
    if row is None or row.used_at is not None:
        return False
    await two_factor_repository.mark_backup_code_used(session, row)
    return True
