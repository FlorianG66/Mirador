# Changelog

Toutes les notables de Mirador sont documentées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versionnage : [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- Backend socle FastAPI (phase 1) : `create_app` avec préfixe `/api/v1`, endpoints `/health` et `/health/db`, erreurs RFC 9457 (`application/problem+json`), logging JSON structuré, configuration pydantic-settings, accès base asyncpg, migrations Alembic (baseline `0001`) et suite pytest sur PostgreSQL réel via pgserver.
- Fondations du repo : structure monorepo, Docker Compose (PostgreSQL), pre-commit, CI avec gitleaks + job backend (ruff, mypy, pytest).
