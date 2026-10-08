# Mirador (nom provisoire)

> SaaS de dashboard « en un coup d'œil » pour entreprises : finance, web analytics, réseaux sociaux, projets & tâches et identité légale, au même endroit.

> **Statut** : projet en cours de développement — phase 2 en cours (auth, organisations, permissions) : sous-phase 2b livrée (inscription, connexion, sessions, CSRF, rate limit d'authentification). Seuls les endpoints d'authentification sont exposés pour l'instant.

## Présentation

Mirador centralise les données de l'entreprise — les dizaines d'outils que le dirigeant ouvre chaque jour — dans un seul tableau de bord : KPI canoniques, widgets personnalisables, alertes. Un admin invite ses collaborateurs et choisit les modules visibles pour chacun.

Le nom est provisoire et le code utilise la constante `PROJECT_NAME`.

## Stack

- **Backend** : Python, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic, PostgreSQL
- **Frontend** : React + TypeScript strict, Vite, TanStack Query, Tailwind CSS, shadcn/ui
- **Outillage** : Docker Compose, pytest, ruff, mypy, Vitest, ESLint, pre-commit, GitHub Actions

Détails et justifications : [`SPEC.md`](SPEC.md) §5, [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Prérequis

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose (base de dev ; les tests ne le nécessitent pas : PostgreSQL éphémère fourni par `pgserver`)
- `pre-commit` et `gitleaks` (voir ci-dessous)

## Installation

```bash
# 1. Variables d'environnement
cp .env.example .env

# 2. Base de données (dev)
docker compose up -d

# 3. Backend (dépendances épinglées dans pyproject.toml)
cd backend
python -m venv .venv
python -m pip install -e ".[dev]"
cd ..

# 4. Hooks de validation (ruff, gitleaks)
pip install pre-commit && pre-commit install
```

## Lancement

```bash
# Backend (settings lus de l'environnement puis .env)
cd backend && python -m uvicorn app.main:create_app --factory --reload

# Frontend (phase 3)
cd frontend && npm run dev
```

## Tests

```bash
# Backend : pytest + couverture (seuil 80 % ; la mesure des coroutines asyncio sous-estime < quelques points, v. DECISIONS)
cd backend && pytest --cov=app

# Qualité backend
cd backend && ruff check . && ruff format --check . && mypy

# Hooks de qualité
pre-commit run --all-files
gitleaks git . -v
```

## Structure du dépôt

```
backend/     API FastAPI (routers, services, repositories, models, schemas, core)
frontend/    SPA React + TypeScript
docs/        SPEC, ROADMAP, ARCHITECTURE, DECISIONS, PROGRESS
infra/       éléments d'infrastructure (hors dépôt privé de production)
.github/     workflows CI, Dependabot
```

## Roadmap

Voir [`ROADMAP.md`](ROADMAP.md) : phases 0-8 = jalon démo/portfolio, 9-11 = jalon commercialisable.

## Licence

[FSL-1.0-Apache-2.0](LICENSE) : usage libre sauf usage concurrent, passage automatique en Apache 2.0 deux ans après publication. Voir `SPEC.md` §12 (validation juridique avant commercialisation).

Le nom « Mirador » et le logo ne sont pas couverts par la licence (marque réservée).
