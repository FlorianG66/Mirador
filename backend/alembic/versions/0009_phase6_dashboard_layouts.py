"""phase 6 : table `dashboard_layouts` (tableau de bord personnalisable) avec RLS

Chaque membre range comme il veut les widgets de la page d'accueil (KPI clés,
santé d'exploitation, objectifs, activité) : sa disposition est mémorisée pour lui
seul, une ligne par couple `(organization_id, user_id)`, en JSONB (`widgets` = liste
de placements `{widget_id, x, y, w, h}`) sur une grille à 12 colonnes (SPEC §4).

Comme les autres tables tenant, la RLS est activée et forcée avec une politique
unique : lecture et écriture restreintes à l'organisation posée par
`app.current_organization_id`.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Paramètre posé par `set_tenant` (app/core/tenancy.py), local à la transaction.
ORGANIZATION_GUC = "current_setting('app.current_organization_id', true)"


def upgrade() -> None:
    op.create_table(
        "dashboard_layouts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "widgets",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "jsonb_typeof(widgets) = 'array'", name="dashboard_layouts_widgets_array"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="dashboard_layouts_org_user"),
    )
    op.create_index(
        op.f("ix_dashboard_layouts_organization_id"),
        "dashboard_layouts",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dashboard_layouts_user_id"), "dashboard_layouts", ["user_id"], unique=False
    )

    _enable_row_level_security()


def _enable_row_level_security() -> None:
    """Active et force la RLS, puis pose la politique unique par organisation."""
    op.execute("ALTER TABLE dashboard_layouts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dashboard_layouts FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY dashboard_layouts_tenant ON dashboard_layouts"
        f" USING (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
        f" WITH CHECK (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE dashboard_layouts DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_dashboard_layouts_user_id"), table_name="dashboard_layouts")
    op.drop_index(op.f("ix_dashboard_layouts_organization_id"), table_name="dashboard_layouts")
    op.drop_table("dashboard_layouts")
