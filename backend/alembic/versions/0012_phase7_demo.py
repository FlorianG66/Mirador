"""phase 7 : organisation de démonstration (`is_demo`) et liens à durée limitée

Le mode démo (SPEC §9) a besoin de distinguer une organisation fictive d'une vraie
organisation cliente. `is_demo`, `demo_sector` et `demo_expires_at` portent ce
marqueur, le scénario sectoriel et l'échéance de la session ; la purge automatique
supprime les organisations arrivées à échéance (données métier en cascade).

`demo_links` stocke les liens `/demo/<token>` générés pour un prospect : seul le
hachage du jeton est conservé, comme pour les sessions et les invitations. Cette
table est globale (hors RLS) : un lien n'appartient pas à un tenant, c'est une
capacité à usage limité.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-22

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SECTOR_VALUES_SQL = "'restaurant', 'agency', 'ecommerce'"


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("organizations", sa.Column("demo_sector", sa.Text(), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("demo_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "organizations_demo_fields",
        "organizations",
        "(NOT is_demo AND demo_sector IS NULL AND demo_expires_at IS NULL)"
        f" OR (is_demo AND demo_sector IN ({SECTOR_VALUES_SQL})"
        " AND demo_expires_at IS NOT NULL)",
    )
    # La purge cherche les démos échues : index partiel, minuscule et ciblé.
    op.create_index(
        "ix_organizations_demo_expires_at",
        "organizations",
        ["demo_expires_at"],
        unique=False,
        postgresql_where=sa.text("is_demo"),
    )

    op.create_table(
        "demo_links",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sector", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(f"sector IN ({SECTOR_VALUES_SQL})", name="demo_links_sector_valid"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="demo_links_token_hash_unique"),
    )
    op.create_index("ix_demo_links_expires_at", "demo_links", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_demo_links_expires_at", table_name="demo_links")
    op.drop_table("demo_links")
    op.drop_index("ix_organizations_demo_expires_at", table_name="organizations")
    op.drop_constraint("organizations_demo_fields", "organizations", type_="check")
    op.drop_column("organizations", "demo_expires_at")
    op.drop_column("organizations", "demo_sector")
    op.drop_column("organizations", "is_demo")
