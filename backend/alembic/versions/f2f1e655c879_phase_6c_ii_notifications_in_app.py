"""phase 6c-ii: notifications in-app

Revision ID: f2f1e655c879
Revises: 0009
Create Date: 2026-10-18 22:46:52.913605

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f2f1e655c879"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORGANIZATION_GUC = "current_setting('app.current_organization_id', true)"


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("dedup_key", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notifications_organization_id"),
        "notifications",
        ["organization_id"],
        unique=False,
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(
        "ix_notifications_org_user_unread",
        "notifications",
        ["organization_id", "user_id", "read_at"],
        unique=False,
    )

    _enable_row_level_security()


def _enable_row_level_security() -> None:
    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notifications FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY notifications_tenant ON notifications"
        f" USING (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
        f" WITH CHECK (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE notifications DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_notifications_org_user_unread", table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_organization_id"), table_name="notifications")
    op.drop_table("notifications")
