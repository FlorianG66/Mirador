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


# Reprise textuelle dans les contraintes CHECK de la base : une seule source de vérité.
ROLE_VALUES_SQL = ", ".join(f"'{role.value}'" for role in Role)
MODULE_VALUES_SQL = ", ".join(f"'{module.value}'" for module in Module)
LEVEL_VALUES_SQL = ", ".join(f"'{level.value}'" for level in PermissionLevel)
