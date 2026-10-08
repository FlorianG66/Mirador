"""Primitives de sécurité : hachage Argon2id, jetons opaques, clé de Luhn du SIREN."""

from __future__ import annotations

from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.core.siren import is_valid_siren


def test_hash_password_uses_argon2id() -> None:
    assert hash_password("mot-de-passe-secret").startswith("$argon2id$")


def test_verify_password_accepts_the_real_one() -> None:
    digest = hash_password("mot-de-passe-secret")
    assert verify_password("mot-de-passe-secret", digest) is True


def test_verify_password_rejects_a_wrong_one() -> None:
    digest = hash_password("mot-de-passe-secret")
    assert verify_password("mot-de-passe-faux", digest) is False


def test_verify_password_rejects_a_corrupted_hash() -> None:
    assert verify_password("mot-de-passe-secret", "pas-un-hachage") is False


def test_two_generated_tokens_are_different_and_url_safe() -> None:
    first, second = generate_token(), generate_token()
    assert first != second
    assert len(first) >= 43  # 32 octets en base64url
    assert "+" not in first and "/" not in first and " " not in first


def test_hash_token_is_stable_and_not_the_token_itself() -> None:
    token = generate_token()
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token


def test_is_valid_siren_accepts_a_luhn_valid_siren() -> None:
    assert is_valid_siren("123456782") is True


def test_is_valid_siren_rejects_a_bad_checksum() -> None:
    assert is_valid_siren("123456789") is False


def test_is_valid_siren_rejects_bad_shapes() -> None:
    assert is_valid_siren("") is False
    assert is_valid_siren("12345678") is False
    assert is_valid_siren("1234567820") is False
    assert is_valid_siren("12345678a") is False
