"""Révision de base.

Aucune table métier à ce stade (elles arrivent en phase 2) : cette révision sert
d'ancrage à l'historique Alembic et valide la chaîne upgrade/downgrade.
"""

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Baseline vide : rien à créer."""


def downgrade() -> None:
    """Baseline vide : rien à supprimer."""
