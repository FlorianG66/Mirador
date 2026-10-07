# Progression

> Fichier de reprise : si tu perds le fil, lis `AGENTS.md`, ce fichier, puis la phase en cours dans `ROADMAP.md`.

## État

- **Phase en cours** : 1 — Backend socle : **terminée en local**, prête à commit sur `phase-1-backend-socle`
- **Prochaine action** : commit phase 1, puis validation par le mainteneur ; ensuite phase 2 (voir `ROADMAP.md`).

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
