"""Validation des identifiants légaux français (SIREN par la clé de Luhn, SPEC §5.4)."""

from __future__ import annotations


def is_valid_siren(value: str) -> bool:
    """Vérifie qu'un SIREN fait exactement 9 chiffres et passe le test de Luhn."""
    if len(value) != 9 or not value.isascii() or not value.isdigit():
        return False
    total = 0
    for position, character in enumerate(reversed(value)):
        digit = int(character)
        if position % 2 == 1:  # double alterné à partir de la droite
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0
