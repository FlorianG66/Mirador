"""phase 8 : table `chat_messages` (historique du chatbot) avec RLS

Comme les autres tables tenant, la RLS est activée et forcée avec une politique
unique : lecture et écriture restreintes à l'organisation posée par
`app.current_organization_id`.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Paramètre posé par `set_tenant` (app/core/tenancy.py), local à la transaction.
ORGANIZATION_GUC = "current_setting('app.current_organization_id', true)"


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="chat_messages_role"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_organization_id"), "chat_messages", ["organization_id"])
    op.create_index(op.f("ix_chat_messages_user_id"), "chat_messages", ["user_id"])
    op.create_index(
        "ix_chat_messages_org_user_created",
        "chat_messages",
        ["organization_id", "user_id", "created_at"],
    )
    op.execute("ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chat_messages FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY chat_messages_tenant ON chat_messages"
        f" USING (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
        f" WITH CHECK (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE chat_messages DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_chat_messages_org_user_created", table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_user_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_organization_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
