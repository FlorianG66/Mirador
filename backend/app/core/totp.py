"""TOTP — RFC 6238, sans dépendance externe (A2F de la phase 2c).

L'implémentation du standard (HMAC-SHA1, 6 chiffres, période 30 s, fenêtre d'un
pas) tient en une vingtaine de lignes et est validée par les vecteurs officiels
de l'appendice B du RFC : pas de bibliothèque à ajouter ni à surveiller
(voir docs/DECISIONS.md). Les fonctions sont pures : le temps est injecté.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from app.core.constants import PROJECT_NAME

TOTP_PERIOD = 30
TOTP_DIGITS = 6
TOTP_WINDOW_STEPS = 1


def generate_totp_secret() -> str:
    """Secret aléatoire en base32 (20 octets), à afficher en QR code ou vignette."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def _code_at(key: bytes, step: int) -> str:
    """Code HOTP à `step` périodes (RFC 4226 appliqué à un compteur de temps)."""
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**TOTP_DIGITS)
    return f"{value:0{TOTP_DIGITS}d}"


def totp_at(secret: str, timestamp: int | None = None) -> str:
    """Code TOTP pour un instant Unix exact ; l'instant courant si non fourni."""
    moment = timestamp if timestamp is not None else int(time.time())
    return _code_at(base64.b32decode(secret.upper()), moment // TOTP_PERIOD)


def verify_totp(
    secret: str,
    code: str,
    *,
    window: int = TOTP_WINDOW_STEPS,
    now: int | None = None,
) -> bool:
    """Vrai si `code` correspond, à `window` période près (tolérance d'horloge)."""
    if not code.isdigit() or len(code) != TOTP_DIGITS:
        return False
    step = (now if now is not None else int(time.time())) // TOTP_PERIOD
    key = base64.b32decode(secret.upper())
    for shift in range(-window, window + 1):
        if _code_at(key, step + shift) == code:
            return True
    return False


def otpauth_url(secret: str, account: str) -> str:
    """URI de provisionnement standard pour les applications d'authentification."""
    label = quote(f"{PROJECT_NAME}:{account}", safe=":@")
    issuer = quote(PROJECT_NAME, safe="")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={issuer}"
        f"&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD}"
    )
