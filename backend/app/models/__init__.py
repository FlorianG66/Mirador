"""Modèles SQLAlchemy (schéma de base).

L'import de chaque table ici remplit `Base.metadata` : Alembic et l'application
voient le schéma complet sans import circulaire (les modèles importent `base`).
"""

from app.models.audit_log import AuditLog
from app.models.auth_challenge import AuthChallenge
from app.models.backup_code import BackupCode
from app.models.base import Base
from app.models.enums import Module, PermissionLevel, Role
from app.models.invitation import Invitation
from app.models.legal_identifier import LegalIdentifier
from app.models.legal_profile import LegalProfile
from app.models.membership import Membership
from app.models.metric_snapshot import MetricSnapshot
from app.models.module_permission import ModulePermission
from app.models.organization import Organization
from app.models.password_reset_token import PasswordResetToken
from app.models.session import UserSession
from app.models.user import User

__all__ = [
    "AuditLog",
    "AuthChallenge",
    "BackupCode",
    "Base",
    "Invitation",
    "LegalIdentifier",
    "LegalProfile",
    "Membership",
    "MetricSnapshot",
    "Module",
    "ModulePermission",
    "Organization",
    "PasswordResetToken",
    "PermissionLevel",
    "Role",
    "User",
    "UserSession",
]
