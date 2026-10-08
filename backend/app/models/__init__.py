"""Modèles SQLAlchemy (schéma de base).

L'import de chaque table ici remplit `Base.metadata` : Alembic et l'application
voient le schéma complet sans import circulaire (les modèles importent `base`).
"""

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.enums import Module, PermissionLevel, Role
from app.models.invitation import Invitation
from app.models.membership import Membership
from app.models.module_permission import ModulePermission
from app.models.organization import Organization
from app.models.session import UserSession
from app.models.user import User

__all__ = [
    "AuditLog",
    "Base",
    "Invitation",
    "Membership",
    "Module",
    "ModulePermission",
    "Organization",
    "PermissionLevel",
    "Role",
    "User",
    "UserSession",
]
