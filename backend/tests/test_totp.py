"""TOTP (RFC 6238) : vecteurs officiels, fenêtre de tolérance, formats.

Les vecteurs viennent de l'appendice B du RFC : secret ASCII « 12345678901234567890 »
(une seule fois en SHA-1), codes à 6 chiffres. Ils garantissent que l'implémentation
n'est pas « presque juste », elle est conforme au standard.
"""

from __future__ import annotations

import base64

from app.core.constants import PROJECT_NAME
from app.core.totp import (
    TOTP_DIGITS,
    TOTP_PERIOD,
    generate_totp_secret,
    otpauth_url,
    totp_at,
    verify_totp,
)

# RFC 6238, appendice B.1 : secret de test. On le décode depuis les octets ASCII
# du RFC (« 12345678901234567890 ») : la forme base32 littérale déclencherait
# gitleaks (valeur à forte entropie ressemblant à une clé).
RFC_SHA1_SECRET = base64.b32encode(b"12345678901234567890").decode("ascii")
RFC_VECTORS: list[tuple[int, str]] = [
    (59, "287082"),
    (1111111109, "081804"),
    (1111111111, "050471"),
    (1234567890, "005924"),
    (2000000000, "279037"),
    (20000000000, "353130"),
]


def test_totp_matches_the_rfc_6238_test_vectors() -> None:
    for timestamp, expected in RFC_VECTORS:
        assert totp_at(RFC_SHA1_SECRET, timestamp) == expected


def test_verify_accepts_the_current_code_when_time_has_moved_one_step() -> None:
    secret = generate_totp_secret()
    base = 1_700_000_130  # aligné sur une période de 30 s.
    code = totp_at(secret, base)

    assert verify_totp(secret, code, now=base)
    assert verify_totp(secret, code, now=base + TOTP_PERIOD)


def test_verify_rejects_a_code_two_steps_old_or_a_fabricated_one() -> None:
    secret = generate_totp_secret()
    base = 1_700_000_130
    code = totp_at(secret, base)

    assert not verify_totp(secret, code, now=base + 2 * TOTP_PERIOD)
    assert not verify_totp(secret, "000000", now=base)
    assert not verify_totp(secret, "abc123", now=base)


def test_generated_secret_is_base32_and_holds_20_random_bytes() -> None:
    secret = generate_totp_secret()

    assert len(base64.b32decode(secret)) == 20
    assert secret == secret.upper()
    assert set(secret) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


def test_otpauth_url_carries_secret_period_and_issuer() -> None:
    url = otpauth_url("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567", "admin@example.com")

    assert url.startswith("otpauth://totp/")
    assert f"{PROJECT_NAME}:admin@example.com" in url
    assert "secret=ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" in url
    assert f"issuer={PROJECT_NAME}" in url
    assert f"period={TOTP_PERIOD}" in url
    assert f"digits={TOTP_DIGITS}" in url
