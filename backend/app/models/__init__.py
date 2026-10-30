"""Modèles SQLAlchemy (schéma de base).

L'import de chaque table ici remplit `Base.metadata` : Alembic et l'application
voient le schéma complet sans import circulaire (les modèles importent `base`).
"""

from app.models.alert_rule import AlertRule
from app.models.audit_log import AuditLog
from app.models.auth_challenge import AuthChallenge
from app.models.backup_code import BackupCode
from app.models.base import Base
from app.models.chat_message import ChatMessage
from app.models.dashboard_layout import DashboardLayout
from app.models.demo_link import DemoLink
from app.models.enums import (
    AlertComparison,
    DemoSector,
    GoalDirection,
    Module,
    PermissionLevel,
    Role,
)
from app.models.goal import Goal
from app.models.invitation import Invitation
from app.models.legal_identifier import LegalIdentifier
from app.models.legal_profile import LegalProfile
from app.models.membership import Membership
from app.models.metric_snapshot import MetricSnapshot
from app.models.module_permission import ModulePermission
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.password_reset_token import PasswordResetToken
from app.models.push_subscription import PushSubscription
from app.models.session import UserSession
from app.models.user import User

__all__ = [
    "AlertRule",
    "AlertComparison",
    "AuditLog",
    "AuthChallenge",
    "BackupCode",
    "Base",
    "ChatMessage",
    "DashboardLayout",
    "DemoLink",
    "DemoSector",
    "Goal",
    "GoalDirection",
    "Invitation",
    "LegalIdentifier",
    "LegalProfile",
    "Membership",
    "MetricSnapshot",
    "Module",
    "ModulePermission",
    "Notification",
    "Organization",
    "PasswordResetToken",
    "PermissionLevel",
    "PushSubscription",
    "Role",
    "User",
    "UserSession",
]
