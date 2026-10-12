# Mirador (nom provisoire)

> SaaS de dashboard « en un coup d'œil » pour entreprises : finance, web analytics, réseaux sociaux, projets & tâches et identité légale, au même endroit.

> **Statut** : projet en cours de développement — phases 0 à 3 livrées et mergées sur `main` (fondations, identité légale, auth & équipe, frontend socle & design system) ; **phase 4 « Connecteurs & données fictives »** mergée (métriques canoniques `module.metric`, connecteurs de démo déterministes par seed, stockage RLS + worker de synchro périodique, endpoint de lecture filtré par tenant et permissions) ; **phase 5 « Modules MVP » sur la branche `phase-5-modules-mvp`** — sous-phases 5a « Finance », 5b « Web analytics », 5c « Réseaux sociaux » et 5d « Projets & tâches » livrées (connecteurs à séries cohérentes + pages `/finance`, `/web`, `/social` et `/projects` complètes : KPI, graphiques Recharts, classements, états chargement/vide/erreur, i18n FR/EN) ; sous-phase **5e « Identité légale »** livrée — 5e-a socle backend (validation SIREN/SIRET/TVA, service de registre `RechercheEntreprisesRegistry`), 5e-b (tables `legal_profiles`/`legal_identifiers` avec RLS, endpoints `GET`/`PUT`/`POST refresh` sous `/organizations/{id}/legal`, provenance par champ et rafraîchissement registre) et 5e-c (page `/legal` : fiche légale avec provenance par champ, dirigeants réservés aux admins, bloc « mentions légales » copiable, saisie manuelle sélective, export PDF, i18n FR/EN) ; sous-phase **5f « Vue d'ensemble Pouls »** livrée (agrégat `GET /organizations/{id}/pulse` : 8 KPI clés des modules autorisés, indicateur de santé opérationnel, fil d'activité réservé aux admins, carte Objectifs à venir en phase 6 ; page d'accueil réécrite, polling 5 min, i18n FR/EN) — **la phase 5 est complète** (clôture et merge à valider par le mainteneur).

## Présentation

Mirador centralise les données de l'entreprise — les dizaines d'outils que le dirigeant ouvre chaque jour — dans un seul tableau de bord : KPI canoniques, widgets personnalisables, alertes. Un admin invite ses collaborateurs et choisit les modules visibles pour chacun.

Le nom est provisoire et le code utilise la constante `PROJECT_NAME`.

## Fonctionnalités (livrées)

- Auth : inscription, connexion, sessions à double jeton (cookies httpOnly), CSRF, rate limiting, Google OIDC, A2F TOTP + codes de secours, réinitialisation de mot de passe par e-mail.
- Équipe : invitations (7 j), rôles admin/membre, permissions par module (view/edit/none, admin = tout), journal d'audit des actions sensibles.
- Fondations : SIREN validé (Luhn), multi-tenant PostgreSQL + Row-Level Security, erreurs RFC 9457, health-check.
- Frontend : design tokens clair/sombre, layout rail + topbar, i18n FR/EN, client API typé généré depuis l'OpenAPI, TanStack Query, gardes de routes par permissions.
- **Phase 4** : métriques canoniques (clé `module.metric`, unité, période, valeur, dimensions JSONB), quatre connecteurs de démo déterministes et réalistes (finance, web, social, projets), stockage tenant + worker de synchro périodique configurable, l'endpoint `GET /organizations/{id}/metrics/{module.metric}` (fenêtre + limite, garde `view` du module).
- **Phase 5 — Modules MVP** : 5a Finance (`MockFinanceConnector`, 8 séries cohérentes, page `/finance`), 5b Web analytics (`MockWebConnector`, 10 séries pilotées par les sessions — visiteurs, pages vues, engagement, durée, conversions, sources, top pages, appareils, pays — page `/web` avec 4 KPI + 9 widgets et répartitions sommant la métrique parente) et 5c Réseaux sociaux (`MockSocialConnector`, 9 séries pilotées par les abonnés — croissance, impressions, portée, interactions, taux d'engagement, mentions, publications, meilleurs posts par réseau — page `/social` avec 4 KPI + 8 widgets) et 5d Projets & tâches (`MockProjectsConnector`, 10 séries pilotées par le stock de tâches ouvertes — créées/terminées, tâches ouvertes/retards, délai moyen de livraison, avancement, projets actifs, répartitions par statut/personne, jalons à venir - page `/projects` avec 4 KPI + 8 widgets), 5e Identité légale (fiche `/legal` : provenance par champ, dirigeants réservés aux admins, mentions légales copiables, export PDF) et 5f Vue d'ensemble « Pouls » (agrégat `GET /organizations/{id}/pulse` : les 8 KPI clés des modules autorisés, indicateur de santé opérationnel, fil d'activité réservé aux admins et carte Objectifs à venir en phase 6 ; page d'accueil réécrite, polling 5 min).

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

# 4. Frontend (versions épinglées exactement dans package.json)
cd frontend
npm install
cd ..
cd ..

# 4. Hooks de validation (ruff, gitleaks)
pip install pre-commit && pre-commit install
```

## Lancement

```bash
# Backend (settings lus de l'environnement puis .env) — attendu sur 127.0.0.1:8000
cd backend && python -m uvicorn app.main:create_app --factory --reload

# Frontend — http://localhost:5173 (le proxy Vite redirige /api/* vers le backend,
# le navigateur reste same-origin : pas de CORS à configurer en dev)
cd frontend && npm run dev
```

## Tests

```bash
# Backend : pytest + couverture (seuil 80 % ; la mesure des coroutines asyncio sous-estime < quelques points, v. DECISIONS)
cd backend && pytest --cov=app

# Qualité backend
cd backend && ruff check . && ruff format --check . && mypy

# Frontend : tests Vitest (jsdom), types, lint, build
cd frontend && npm test && npm run typecheck && npm run lint && npm run build

# Hooks de qualité
pre-commit run --all-files
gitleaks git . -v
```

## Structure du dépôt

```
backend/     API FastAPI (routers, services, repositories, models, schemas, core)
frontend/    SPA Vite + React + TypeScript strict (src/, tests, config ESLint/Vitest)
docs/        SPEC, ROADMAP, ARCHITECTURE, DECISIONS, PROGRESS
infra/       éléments d'infrastructure (hors dépôt privé de production)
.github/     workflows CI, Dependabot
```

## Roadmap

Voir [`ROADMAP.md`](ROADMAP.md) : phases 0-8 = jalon démo/portfolio, 9-11 = jalon commercialisable.

## Licence

[FSL-1.0-Apache-2.0](LICENSE) : usage libre sauf usage concurrent, passage automatique en Apache 2.0 deux ans après publication. Voir `SPEC.md` §12 (validation juridique avant commercialisation).

Le nom « Mirador » et le logo ne sont pas couverts par la licence (marque réservée).
