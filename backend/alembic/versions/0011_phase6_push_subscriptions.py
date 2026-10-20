"""phase 6c-iii-b : table `push_subscriptions` (abonnements Web Push) avec RLS

Un abonnement relie un utilisateur d'une organisation à un endpoint de push fourni
par le navigateur (avec ses clés `p256dh`/`auth`). L'envoi passe par le service de
push standard (VAPID) ; le backend ne stocke que de quoi pousser un message.

Comme les autres tables tenant, la RLS est activée et forcée avec une politique
unique : lecture et écriture restreintes à l'organisation posée par
`app.current_organization_id`. L'endpoint est unique : un navigateur qui se
réabonne met à jour sa ligne au lieu d'en créer une seconde.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Paramètre posé par `set_tenant` (app/core/tenancy.py), local à la transaction.
ORGANIZATION_GUC = "current_setting('app.current_organization_id', true)"


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint", name="push_subscriptions_endpoint_unique"),
    )
    op.create_index(
        op.f("ix_push_subscriptions_organization_id"),
        "push_subscriptions",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_push_subscriptions_user_id"),
        "push_subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_push_subscriptions_org_user",
        "push_subscriptions",
        ["organization_id", "user_id"],
        unique=False,
    )

    _enable_row_level_security()


def _enable_row_level_security() -> None:
    """Active et force la RLS, puis pose la politique unique par organisation."""
    op.execute("ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE push_subscriptions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY push_subscriptions_tenant ON push_subscriptions"
        f" USING (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
        f" WITH CHECK (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE push_subscriptions DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_push_subscriptions_org_user", table_name="push_subscriptions")
    op.drop_index(op.f("ix_push_subscriptions_user_id"), table_name="push_subscriptions")
    op.drop_index(op.f("ix_push_subscriptions_organization_id"), table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
