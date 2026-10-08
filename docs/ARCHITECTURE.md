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
  main.py       create_app(settings) : assemblage (logging, routes, erreurs, engine)
  routers/      HTTP uniquement, aucune logique métier
  services/     logique métier
  repositories/ accès aux données
  models/       modèles SQLAlchemy
  schemas/      schémas Pydantic (entrée/sortie)
  core/         config (pydantic-settings), erreurs RFC 9457, logging JSON,
                base asyncpg, tenancy (GUC tenant), deps (session par requête)
```

Couches : `routers → services → repositories`.

- **Multi-tenant** : `users` et `organizations` sont globales (hors RLS) ; `memberships`, `module_permissions`, `invitations`, `audit_logs` portent `organization_id` avec RLS `ENABLE` + `FORCE` et **une seule politique** par table. `app.core.tenancy.set_tenant` pose deux GUC transactionnels (`app.current_user_id`, `app.current_organization_id`) ; `USING` lit l'organisation **ou** l'utilisateur courant, `WITH CHECK` n'accepte que l'organisation courante (empêche l'auto-insertion dans un tenant tiers).
- **Session par requête** : `app.core.deps.get_session` récupère la fabrique sur `app.state.session_factory`, commit en fin de succès, rollback sinon, tenant neutre au démarrage.
- **Repositories** : filtrage explicite **et** RLS (double barrière) ; e-mail des utilisateurs normalisé en minuscules.
- **Sessions** : table `sessions` globale (hors RLS, comme `users`) ; jetons opaques aléatoires, seuls leurs hachages SHA-256 sont stockés ; rotation des deux jetons à chaque rafraîchissement, révocation au logout ; le jeton CSRF appartient à la session (il ne tourne pas).
- **Authentification** : cookies httpOnly + `SameSite=lax` — accès `Path=/` (TTL 15 min), refresh confiné à `Path=/api/v1/auth` (TTL 30 j), CSRF lisible par le JS `Path=/` ; en production les trois sont `Secure`. Mots de passe Argon2id (params OWASP) ; e-mail normalisé ; SIREN facultatif vérifié (9 chiffres + Luhn) ; un message d'erreur unique quels que soient e-mail/mot de passe (aucune énumération, hachage factice pour le minutage).
- **Sécurité transverse** (`app/core/middleware.py`) : en-têtes de sécurité sur toutes les réponses et CSRF double submit — le cookie `mirador_csrf` doit être repris dans l'en-tête `X-CSRF-Token`, exigé seulement pour les écritures **avec** cookie d'authentification (le 405 d'une route inconnue reste un 405) ; `/auth/register` et `/auth/login` sont exemptées (elles distribuent le jeton).
- **Rate limit** (`app/core/rate_limit.py`) : fenêtre glissante en mémoire par couple (route, IP) sur `app.state.rate_limiter`, 429 + `Retry-After` au-delà du quota ; un répartiteur ou plusieurs processus devront partager un compteur (v. `DECISIONS.md`).

- **API** : préfixe `/api/v1` ; `/health` (vivacité, sans base) et `/health/db` (200 si PostgreSQL répond, 503 en `application/problem+json` sinon).
- **Erreurs** : handlers globaux (404, 405, 422, 500) au format RFC 9457, titres = phrases HTTP ; jamais d'erreur 500 brute ni de fuite de détail.
- **Logging** : handler unique JSON sur le logger `app` (tous les modules `app.*` y propagent), `propagate=False`, idempotent.
- **Config** : `Settings` (env → `.env`), URL forcée en `postgresql+asyncpg://` ; les settings sont portés par `app.state` et injectés en test via `create_app`.
- **Migrations** : Alembic async (`alembic/env.py` lit les settings), baseline `0001` + `0002` (6 tables phase 2 et RLS) + `0003` (table `sessions`).
- **Tests** : `pgserver` lance PostgreSQL 16.2 éphémère pour les tests (CI incluse, sans Docker) ; seuil de couverture 80 % ; base vidée avant chaque test (isolation des e-mails uniques).

## Structure frontend

SPA React (Vite) derrière login : pas de SSR (le backend est déjà FastAPI). Client API généré depuis l'OpenAPI. Voir `SPEC.md` §5.2.

## Environnements

- **Dev** : Docker Compose (PostgreSQL avec volume persistant), `.env.example` en modèle.
- **CI** : lint (ruff, eslint), types (mypy, tsc), tests (pytest, Vitest), gitleaks, audit des dépendances.
- **Production** : PaaS managé français (voir `SPEC.md` §10), config d'infra dans un dépôt privé séparé.
