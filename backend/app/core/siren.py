"""Validation des identifiants légaux français (SPEC §5.4).

SIREN (9 chiffres) et SIRET (14 chiffres) sont contrôlés par la clé de Luhn ; le
numéro de TVA intracommunautaire est calculé à partir du SIREN. La clé de Luhn a
des exceptions connues (par exemple certains établissements de La Poste) : elles
ne sont **pas** traitées ici, faute de documentation officielle vérifiée — un
identifiant légitime de ce type sera marqué invalide, à corriger le jour où la
règle sera confirmée.
"""

from __future__ import annotations

VAT_PREFIX = "FR"


def _luhn_is_valid(value: str) -> bool:
    """Clé de Luhn : somme alternée des chiffres (doublement à partir de la droite)."""
    total = 0
    for position, character in enumerate(reversed(value)):
        digit = int(character)
        if position % 2 == 1:  # double alterné à partir de la droite
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _is_digits(value: str, length: int) -> bool:
    return len(value) == length and value.isascii() and value.isdigit()


def is_valid_siren(value: str) -> bool:
    """Vérifie qu'un SIREN fait exactement 9 chiffres et passe le test de Luhn."""
    return _is_digits(value, 9) and _luhn_is_valid(value)


def is_valid_siret(value: str) -> bool:
    """Vérifie qu'un SIRET fait exactement 14 chiffres et passe le test de Luhn."""
    return _is_digits(value, 14) and _luhn_is_valid(value)


def french_vat_key(siren: str) -> str:
    """Clé de TVA française sur deux chiffres, calculée depuis le SIREN (SPEC §5.4).

    Formule : `(12 + 3 × (SIREN mod 97)) mod 97`. Le SIREN doit être valide (Luhn) :
    calculer une clé sur un SIREN erroné produirait un numéro trompeur.
    """
    if not is_valid_siren(siren):
        raise ValueError("SIREN invalide : la clé de TVA ne peut pas être calculée.")
    key = (12 + 3 * (int(siren) % 97)) % 97
    return f"{key:02d}"


def french_vat_number(siren: str) -> str:
    """Numéro de TVA intracommunautaire français : `FR` + clé + SIREN (SPEC §5.4).

    La TVA est purement calculée : une entreprise peut avoir un SIREN valide sans
    numéro de TVA, donc ce numéro n'est jamais exigé (SPEC §5.4).
    """
    return f"{VAT_PREFIX}{french_vat_key(siren)}{siren}"
