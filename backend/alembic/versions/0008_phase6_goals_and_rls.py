"""phase 6 : table `goals` (objectifs et budgets) avec Row-Level Security

Un objectif cible n'importe quel KPI canonique (`module.metric`) sur une fenêtre
glissante (`period_days`) avec un sens (`at_least` / `at_most`) et une valeur
cible (SPEC §4). La progression et l'alerte de dérive se recalculent à la lecture,
elles ne sont donc pas stockées.

Comme les autres tables tenant, la RLS est activée et forcée avec une politique
unique : lecture et écriture restreintes à l'organisation posée par
`app.current_organization_id`.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-12

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Paramètre posé par `set_tenant` (app/core/tenancy.py), local à la transaction.
ORGANIZATION_GUC = "current_setting('app.current_organization_id', true)"

# Les mêmes expressions que dans les modèles : ne pas diverger.
_METRIC_KEY_REGEX = r"^(finance|legal|projects|social|web)\.[a-z0-9_]+$"
_GOAL_DIRECTION_VALUES_SQL = "'at_least', 'at_most'"


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("metric_key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("target_value", sa.Double(), nullable=False),
        sa.Column("period_days", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(f"metric_key ~ '{_METRIC_KEY_REGEX}'", name="goals_key_format"),
        sa.CheckConstraint(
            f"direction IN ({_GOAL_DIRECTION_VALUES_SQL})", name="goals_direction_known"
        ),
        sa.CheckConstraint("period_days BETWEEN 1 AND 365", name="goals_period_days_range"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_goals_organization_id"), "goals", ["organization_id"], unique=False)

    _enable_row_level_security()


def _enable_row_level_security() -> None:
    """Active et force la RLS, puis pose la politique unique par organisation."""
    op.execute("ALTER TABLE goals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE goals FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY goals_tenant ON goals"
        f" USING (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
        f" WITH CHECK (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE goals DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_goals_organization_id"), table_name="goals")
    op.drop_table("goals")
