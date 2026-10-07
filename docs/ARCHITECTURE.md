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
  routers/      HTTP uniquement, aucune logique métier
  services/     logique métier
  repositories/ accès aux données
  models/       modèles SQLAlchemy
  schemas/      schémas Pydantic (entrée/sortie)
  core/         config, erreurs (RFC 9457), dépendances partagées
```

Couches : `routers → services → repositories`.

## Structure frontend

SPA React (Vite) derrière login : pas de SSR (le backend est déjà FastAPI). Client API généré depuis l'OpenAPI. Voir `SPEC.md` §5.2.

## Environnements

- **Dev** : Docker Compose (PostgreSQL avec volume persistant), `.env.example` en modèle.
- **CI** : lint (ruff, eslint), types (mypy, tsc), tests (pytest, Vitest), gitleaks, audit des dépendances.
- **Production** : PaaS managé français (voir `SPEC.md` §10), config d'infra dans un dépôt privé séparé.
