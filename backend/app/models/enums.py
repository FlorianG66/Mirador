"""Énumérations du domaine : rôles, modules permissionnables, niveaux d'accès (SPEC §2)."""

from enum import StrEnum


class Role(StrEnum):
    """Rôle d'un membre au sein d'une organisation (SPEC §2)."""

    ADMIN = "admin"
    MEMBER = "member"


class Module(StrEnum):
    """Modules du MVP rendus permissionnables (SPEC §3)."""

    FINANCE = "finance"
    WEB = "web"
    SOCIAL = "social"
    PROJECTS = "projects"
    LEGAL = "legal"


class PermissionLevel(StrEnum):
    """Niveau d'accès d'un membre sur un module : none / view / edit (SPEC §2)."""

    NONE = "none"
    VIEW = "view"
    EDIT = "edit"


class GoalDirection(StrEnum):
    """Sens d'un objectif (SPEC §4) : viser au moins la cible, ou rester en dessous.

    `at_least` pour une cible à atteindre (chiffre d'affaires, abonnés) ; `at_most`
    pour un plafond à ne pas dépasser (budget de dépenses, tâches en retard).
    """

    AT_LEAST = "at_least"
    AT_MOST = "at_most"


class AlertComparison(StrEnum):
    """Sens de franchissement d'une règle d'alerte (SPEC §4) : dépasser ou passer sous.

    `above` = la valeur de la fenêtre dépasse le seuil (facture impayée élevée,
    dépenses qui débordent) ; `below` = elle passe sous le seuil (CA qui plonge,
    visites en chute).
    """

    ABOVE = "above"
    BELOW = "below"


# Reprise textuelle dans les contraintes CHECK de la base : une seule source de vérité.
ROLE_VALUES_SQL = ", ".join(f"'{role.value}'" for role in Role)
MODULE_VALUES_SQL = ", ".join(f"'{module.value}'" for module in Module)
LEVEL_VALUES_SQL = ", ".join(f"'{level.value}'" for level in PermissionLevel)
GOAL_DIRECTION_VALUES_SQL = ", ".join(f"'{direction.value}'" for direction in GoalDirection)
ALERT_COMPARISON_VALUES_SQL = ", ".join(f"'{item.value}'" for item in AlertComparison)
