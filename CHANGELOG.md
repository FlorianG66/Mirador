# Changelog

Toutes les notables de Mirador sont documentées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versionnage : [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- Modèle de données phase 2, sous-phase 2a : tables `organizations`, `users` (globales) et `memberships`, `module_permissions`, `invitations`, `audit_logs` (tenants, RLS activée et forcée, une politique par table), migration Alembic `0002`, gestion du tenant par GUC transactionnels, session par requête (`get_session`) et repositories `organizations` / `users` / `memberships`.
- Backend socle FastAPI (phase 1) : `create_app` avec préfixe `/api/v1`, endpoints `/health` et `/health/db`, erreurs RFC 9457 (`application/problem+json`), logging JSON structuré, configuration pydantic-settings, accès base asyncpg, migrations Alembic (baseline `0001`) et suite pytest sur PostgreSQL réel via pgserver.
- Fondations du repo : structure monorepo, Docker Compose (PostgreSQL), pre-commit, CI avec gitleaks + job backend (ruff, mypy, pytest).
