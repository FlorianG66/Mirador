"""Tests d'Alembic : aller-retour des migrations et schéma de la phase 2."""

from __future__ import annotations

from alembic import command
from tests.conftest import alembic_config, fetch_scalar, upgrade_to_head

BASELINE_REVISION = "0001"
HEAD_REVISION = "0004"

# Tables soumises à Row-Level Security : elles portent toutes organization_id.
TENANT_TABLES = ("memberships", "module_permissions", "invitations", "audit_logs")
# Globals d'identité (comme `users` et `sessions`) : hors RLS, phase 2c.
IDENTITY_TABLES = ("auth_challenges", "backup_codes", "password_reset_tokens")


def test_upgrade_head_then_downgrade_base_round_trip(alembic_test_database_url: str) -> None:
    config = alembic_config(alembic_test_database_url)

    command.upgrade(config, "head")

    revision = fetch_scalar(alembic_test_database_url, "SELECT version_num FROM alembic_version")
    assert revision == HEAD_REVISION
    table_exists = fetch_scalar(alembic_test_database_url, "SELECT to_regclass('organizations')")
    assert table_exists is not None

    command.downgrade(config, "base")

    # Alembic vide l'historique mais conserve la table : vérifier l'absence de version
    # et l'absence de table suffit (constaté, pas supposé).
    version = fetch_scalar(alembic_test_database_url, "SELECT version_num FROM alembic_version")
    assert version is None
    table_exists = fetch_scalar(alembic_test_database_url, "SELECT to_regclass('organizations')")
    assert table_exists is None


def test_upgrade_from_baseline_reaches_phase2(alembic_test_database_url: str) -> None:
    """La révision de base 0001 existe bien : l'historique n'est pas orphelin."""
    config = alembic_config(alembic_test_database_url)

    command.upgrade(config, BASELINE_REVISION)
    assert fetch_scalar(alembic_test_database_url, "SELECT version_num FROM alembic_version") == (
        BASELINE_REVISION
    )

    upgrade_to_head(alembic_test_database_url)
    assert fetch_scalar(alembic_test_database_url, "SELECT version_num FROM alembic_version") == (
        HEAD_REVISION
    )


def test_tenant_tables_enforce_row_level_security(alembic_test_database_url: str) -> None:
    """Défense en profondeur (AGENTS.md §5) : RLS activée ET forcée sur chaque table tenant."""
    upgrade_to_head(alembic_test_database_url)

    for table in TENANT_TABLES:
        enabled = fetch_scalar(
            alembic_test_database_url,
            f"SELECT relrowsecurity AND relforcerowsecurity FROM pg_class"
            f" WHERE oid = to_regclass('{table}')",
        )
        assert enabled is True, f"RLS activée et forcée sur {table}"

    policy_count = fetch_scalar(
        alembic_test_database_url,
        "SELECT count(*) FROM pg_policies WHERE schemaname = 'public'",
    )
    assert policy_count == len(TENANT_TABLES)


def test_phase2_tables_created_by_migration(alembic_test_database_url: str) -> None:
    upgrade_to_head(alembic_test_database_url)

    for table in (*TENANT_TABLES, *IDENTITY_TABLES, "organizations", "users", "sessions"):
        exists = fetch_scalar(alembic_test_database_url, f"SELECT to_regclass('{table}')")
        assert exists is not None, f"table {table} absente du schéma"


def test_two_factor_columns_added_to_users(alembic_test_database_url: str) -> None:
    """Phase 2c : le compte porte le secret (nullable) et la date d'activation TOTP."""
    upgrade_to_head(alembic_test_database_url)

    columns = fetch_scalar(
        alembic_test_database_url,
        "SELECT string_agg(column_name, ',' ORDER BY column_name)"
        " FROM information_schema.columns WHERE table_name = 'users'",
    )
    assert isinstance(columns, str)
    assert "totp_secret" in columns
    assert "totp_enabled_at" in columns


def test_sessions_stay_out_of_row_level_security(alembic_test_database_url: str) -> None:
    """`sessions` est un global d'identité (comme `users`) : la RLS ne la concerne pas."""
    upgrade_to_head(alembic_test_database_url)

    row_level_security = fetch_scalar(
        alembic_test_database_url,
        "SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass('sessions')",
    )
    assert row_level_security is False


def test_two_factor_tables_stay_out_of_row_level_security(alembic_test_database_url: str) -> None:
    """Défis, codes de secours et jetons de réinitialisation : pas de tenant (phase 2c)."""
    upgrade_to_head(alembic_test_database_url)

    for table in IDENTITY_TABLES:
        row_level_security = fetch_scalar(
            alembic_test_database_url,
            f"SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass('{table}')",
        )
        assert row_level_security is False
