# Progression

> Fichier de reprise : si tu perds le fil, lis `AGENTS.md`, ce fichier, puis la phase en cours dans `ROADMAP.md`.

## État

- **Phase en cours** : 2 — Auth, organisations, permissions. Découpage en sous-phases :
  2a modèle + RLS + repositories (**livrée et commitée**), 2b inscription/connexion/sessions/CSRF/rate-limit,
  2c A2F TOTP + codes de secours + mot de passe oublié, 2d invitations/permissions/révocation/audit, 2e Google OIDC.
- **Branche** : `phase-2-auth-organisations` (créée depuis `phase-1-backend-socle`).
- **Prochaine action** : passer à la sous-phase 2b — inscription, connexion, sessions, CSRF, rate-limit.
- **À ne pas faire** : merger sur `main` sans feu vert du mainteneur.

### Critères de la phase 0 — vérité du terrain
| Critère | État |
|---|---|
| `docker compose up` démarre la base | ❌ **non vérifié** : Docker absent de cette machine (fichier `docker-compose.yml` écrit, image `postgres:18.6` tag vérifié sur Docker Hub) |
| CI s'exécute et passe | ⚠️ **non vérifié** : aucun remote GitHub configuré. Config YAML validée, commande gitleaks de la CI testée en local |
| gitleaks ne détecte rien | ✅ vérifié : `gitleaks dir .` + `gitleaks git --pre-commit --staged` → « no leaks found » |
| pre-commit passe | ✅ `pre-commit run --all-files` exit 0 |

### Critères de la phase 1 — vérité du terrain
| Critère | État |
|---|---|
| Tests écrits d'abord (RED) puis GREEN | ✅ 30 tests : RED vérifié (21 failed + 5 errors) avant toute implémentation, puis GREEN (30 passed) |
| pytest vert | ✅ `pytest --cov=app` → 30 passed |
| Couverture ≥ 80 % | ✅ **100 %** (144 lignes, 0 manquantes) |
| ruff check + format | ✅ exit 0 / 26 fichiers conformes |
| mypy strict | ✅ 0 erreur sur 16 fichiers |
| Tests base réelle (PostgreSQL) | ✅ pgserver 16.2 : `/health/db` 200 + 503 injoignable, aller-retour Alembic |
| CI backend | ⚠️ job écrit, **non exécuté** (aucun remote GitHub) |
| pre-commit passe | ✅ relancé avant commit |

### Critères de la phase 2a — vérité du terrain
| Critère | État |
|---|---|
| Tests écrits d'abord (RED) puis GREEN | ✅ RED avant toute implémentation : **25 failed + 5 errors** (29 passed) ; GREEN : **55 passed** |
| pytest vert | ✅ `pytest --cov=app` → 55 passed |
| Couverture ≥ 80 % | ✅ **100 %** (345 lignes, 0 manquantes) |
| ruff check + format | ✅ exit 0 / 43 fichiers conformes |
| mypy strict | ✅ 0 erreur sur 28 fichiers |
| Migrations Alembic | ✅ `0002` autogénérée : 6 tables, aller-retour `head → base` vérifié sur base jetable |
| RLS réelle | ✅ `ENABLE` + `FORCE` sur `memberships`, `module_permissions`, `invitations`, `audit_logs` ; exactement 4 politiques ; tests d'isolation **en rôle non-superuser** |
| Tests base réelle (PostgreSQL) | ✅ pgserver 16.2 partagé + bases jetables par test d'Alembic |
| pre-commit passe | ✅ `pre-commit run --all-files` → 9 hooks Passed |
| gitleaks ne détecte rien | ✅ `gitleaks git . --redact` → « no leaks found » (2 commits) |
| CI backend | ⚠️ job écrit, **non exécuté** (aucun remote GitHub) |

### Pièges rencontrés en phase 2a (à ne pas re-piocher)
- **`removeprefix` au lieu de `replace`** : `_raw_pg_url` produisait `postgres:@host` au lieu de `postgresql://postgres:@host` → `ConnectionRefusedError` incompréhensible. Le schéma doit être remplacé, pas supprimé.
- **Le rôle `postgres` est superuser** : PostgreSQL le fait toujours passer avant la RLS (`FORCE` ne s'applique qu'au propriétaire). Les tests d'isolation se connectent donc en `mirador_test` (LOGIN, sans droits sur le schéma avant `GRANT`), sinon ils ne testent rien.
- **Isolation des tests** : `db_session` n'annule que ce qui n'a pas été commité ; deux tests qui commitent le même e-mail entrent en conflit → un e-mail unique par test.

### À faire au premier push GitHub (réglages de dépôt, hors code)
- Secret scanning + push protection, protection de la branche `main`, Dependabot actif.

## Historique

### 2026-10-07 — Démarrage
- Lu `SPEC.md` et `ROADMAP.md` (à la racine, pas dans `docs/`).
- Dépôt vierge : aucun commit, 3 fichiers de cadrage.
- Environnement : Python 3.12.10, Node 24.19, git 2.54 — **pas de Docker ni de PostgreSQL** sur la machine.
- Sous-phase 0a en cours : structure monorepo, fichiers racine, Compose, pre-commit, CI.

### 2026-10-07 — Phase 0 livrée (en local)
- Structure monorepo + fichiers racine (README, CHANGELOG, SECURITY, CONTRIBUTING, LICENSE FSL-1.0-Apache-2.0, .gitignore, .editorconfig, .gitattributes).
- `docker-compose.yml` (postgres:18.6, volume persistant, healthcheck) + `.env.example`.
- pre-commit : pre-commit-hooks v6.0.0, ruff v0.16.10, hook local gitleaks (le hook upstream système acceptait les noms de fichiers → plantait, corrigé), hook eslint prêt pour la phase 3.
- CI GitHub Actions : job gitleaks (gitleaks v8.30.1 épinglé, scan de tout l'historique) ; Dependabot (actions, pip, npm, docker).
- Vérifications : `pre-commit run --all-files` ✅ · `gitleaks` ✅ · Docker/CI non vérifiables sans Docker ni remote (voir tableau ci-dessus).

### 2026-10-07 — Phase 1 livrée (en local)
- Branche `phase-1-backend-socle`. TDD respecté : tests RED d'abord (21 failed + 5 errors sur stubs `NotImplementedError`), implémentation GREEN ensuite.
- Socle : `create_app(settings)` (préfixe `/api/v1`), `/health` + `/health/db`, erreurs RFC 9457, logging JSON (logger `app`), pydantic-settings, asyncpg, Alembic baseline `0001`.
- Base de test : `pgserver==0.1.4` → PostgreSQL 16.2 éphémère réel (remplace la limite « pas de PostgreSQL » de la phase 0).
- Écarts de conception corrigés en cours de route (constatés par les tests) : logger réel `app.*` (pas `mirador.*`), pytest injecte ses handlers sur les loggers non-propagants (compter nos handlers via `JsonFormatter`), Alembic conserve `alembic_version` vidée après downgrade.
- Vérifications : 30 passed · couverture 100 % · ruff ✅ · format ✅ · mypy strict ✅ · CI backend ajoutée (non exécutée sans remote).

### 2026-10-07 — Sous-phase 2a livrée (en local)
- Branche `phase-2-auth-organisations`. TDD respecté : RED (25 failed + 5 errors) avant toute implémentation.
- Schéma : `organizations`, `users` (globaux, hors RLS), `memberships`, `module_permissions`, `invitations`, `audit_logs` (tenants, RLS activée + forcée, une politique par table).
- Multi-tenant : `app.core.tenancy.set_tenant` pose deux GUC transactionnels (`app.current_user_id`, `app.current_organization_id`, `is_local=true`) ; `app.core.deps.get_session` donne une session par requête (commit en fin de succès, rollback sinon, tenant neutre au départ).
- Repositories : `organizations`, `users` (e-mail normalisé en minuscules), `memberships` (filtre explicite **et** RLS).
- `create_app` crée maintenant l'engine + la fabrique de sessions (`app.state.engine`, `app.state.session_factory`) et dispose le pool dans un lifespan.
- Infrastructure de test : bases jetables par test d'Alembic, rôle `mirador_test` non-superuser, fixtures `app`/`client`/`db_session`.
- Vérifications : 55 passed · couverture 100 % · ruff ✅ · format ✅ · mypy strict ✅ · pre-commit ✅ · gitleaks ✅ · CI non exécutée sans remote.
- **Non fait** : commit (en attente), documentation `ARCHITECTURE.md` / `CHANGELOG.md` / `README.md` à compléter au moment du commit de fin de sous-phase.

### 2026-10-08 — Sous-phase 2a commitée
- Revérification avant commit : `pytest --cov=app` → 55 passed, couverture 100 % · ruff check/format ✅ · mypy strict ✅ (28 fichiers) · `pre-commit run --all-files` → 10 hooks ✅ · `gitleaks git . --redact` → no leaks found.
- Docs mises à jour : `ARCHITECTURE.md` (tenant, session par requête, repositories), `CHANGELOG.md`, `README.md` (statut phase 2), `PROGRESS.md`.
- Push impossible : aucun remote GitHub configuré (voir « À faire au premier push »).
