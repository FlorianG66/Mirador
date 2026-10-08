"""phase 2b : table des sessions d'authentification

Deux jetons opaques par session (accès court, rafraîchissement long avec
rotation) dont seul l'hachage SHA-256 est stocké, plus le jeton CSRF renvoyé
au navigateur dans un cookie lisible.

`sessions` est un global d'identité comme `users` : pas de RLS (voir
docs/DECISIONS.md), l'isolation se joue sur les memberships.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("access_token_hash", sa.Text(), nullable=False),
        sa.Column("refresh_token_hash", sa.Text(), nullable=False),
        sa.Column("csrf_token", sa.Text(), nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("access_token_hash"),
        sa.UniqueConstraint("refresh_token_hash"),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_table("sessions")
