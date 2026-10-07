# Architecture — Mirador

> Vue d'ensemble technique. Le détail et les justifications sont dans `SPEC.md` §5 ; l'avancement dans `PROGRESS.md`.

## Flux de données

```
[Outils tiers] --API / webhooks / MCP--> [Connecteurs] --> [Métriques canoniques]
                                                                      |
[Planificateur 5 min] -------------------------------------> [PostgreSQL] <--> [API FastAPI] <--> [Frontend React]
```

- **Connecteurs** (cœur du produit) : interface `Connector` unique ; un `MockConnector` par catégorie produit exactement le même format qu'un connecteur réel, déterministe via un seed.
- **Métriques canoniques** : clé `module.metric` (ex. `finance.revenue`), unité, période, valeur, dimensions JSONB.
- **Multi-tenant** : chaque table métier porte `organization_id`, chaque requête est filtrée dessus, PostgreSQL RLS en défense en profondeur.

## Structure backend

```
backend/app/
  main.py       create_app(settings) : assemblage (logging, routes, erreurs)
  routers/      HTTP uniquement, aucune logique métier
  services/     logique métier
  repositories/ accès aux données
  models/       modèles SQLAlchemy
  schemas/      schémas Pydantic (entrée/sortie)
  core/         config (pydantic-settings), erreurs RFC 9457, logging JSON, base asyncpg
```

Couches : `routers → services → repositories`.

- **API** : préfixe `/api/v1` ; `/health` (vivacité, sans base) et `/health/db` (200 si PostgreSQL répond, 503 en `application/problem+json` sinon).
- **Erreurs** : handlers globaux (404, 405, 422, 500) au format RFC 9457, titres = phrases HTTP ; jamais d'erreur 500 brute ni de fuite de détail.
- **Logging** : handler unique JSON sur le logger `app` (tous les modules `app.*` y propagent), `propagate=False`, idempotent.
- **Config** : `Settings` (env → `.env`), URL forcée en `postgresql+asyncpg://` ; les settings sont portés par `app.state` et injectés en test via `create_app`.
- **Migrations** : Alembic async (`alembic/env.py` lit les settings), baseline `0001` (tables métiers en phase 2).
- **Tests** : `pgserver` lance PostgreSQL 16.2 éphémère pour les tests (CI incluse, sans Docker) ; seuil de couverture 80 %.

## Structure frontend

SPA React (Vite) derrière login : pas de SSR (le backend est déjà FastAPI). Client API généré depuis l'OpenAPI. Voir `SPEC.md` §5.2.

## Environnements

- **Dev** : Docker Compose (PostgreSQL avec volume persistant), `.env.example` en modèle.
- **CI** : lint (ruff, eslint), types (mypy, tsc), tests (pytest, Vitest), gitleaks, audit des dépendances.
- **Production** : PaaS managé français (voir `SPEC.md` §10), config d'infra dans un dépôt privé séparé.
