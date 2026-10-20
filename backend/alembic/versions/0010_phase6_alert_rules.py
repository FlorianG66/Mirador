"""phase 6c-iii : table `alert_rules` (règles d'alerte configurables) avec RLS

Une règle surveille une clé canonique (`module.metric`) sur une fenêtre glissante
(`period_days`) et se déclenche quand la valeur agrégée franchit un seuil dans le
sens `comparison` (`above` / `below`). Ni l'état courant ni l'historique ne sont
stockés : l'évaluation lit les `metric_snapshots` et la déduplication s'appuie sur
les notifications non lues (SPEC §4).

Comme les autres tables tenant, la RLS est activée et forcée avec une politique
unique : lecture et écriture restreintes à l'organisation posée par
`app.current_organization_id`.

Revision ID: 0010
Revises: f2f1e655c879
Create Date: 2026-10-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "f2f1e655c879"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Paramètre posé par `set_tenant` (app/core/tenancy.py), local à la transaction.
ORGANIZATION_GUC = "current_setting('app.current_organization_id', true)"

# Les mêmes expressions que dans les modèles : ne pas diverger.
_METRIC_KEY_REGEX = r"^(finance|legal|projects|social|web)\.[a-z0-9_]+$"
_ALERT_COMPARISON_VALUES_SQL = "'above', 'below'"


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("metric_key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("comparison", sa.Text(), nullable=False),
        sa.Column("threshold", sa.Double(), nullable=False),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint(f"metric_key ~ '{_METRIC_KEY_REGEX}'", name="alert_rules_key_format"),
        sa.CheckConstraint(
            f"comparison IN ({_ALERT_COMPARISON_VALUES_SQL})", name="alert_rules_comparison_known"
        ),
        sa.CheckConstraint("period_days BETWEEN 1 AND 365", name="alert_rules_period_days_range"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_alert_rules_organization_id"),
        "alert_rules",
        ["organization_id"],
        unique=False,
    )

    _enable_row_level_security()


def _enable_row_level_security() -> None:
    """Active et force la RLS, puis pose la politique unique par organisation."""
    op.execute("ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alert_rules FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY alert_rules_tenant ON alert_rules"
        f" USING (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
        f" WITH CHECK (organization_id = NULLIF({ORGANIZATION_GUC}, '')::uuid)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE alert_rules DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_alert_rules_organization_id"), table_name="alert_rules")
    op.drop_table("alert_rules")
