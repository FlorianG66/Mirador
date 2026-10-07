# Progression

> Fichier de reprise : si tu perds le fil, lis `AGENTS.md`, ce fichier, puis la phase en cours dans `ROADMAP.md`.

## État

- **Phase en cours** : 0 — Fondations du repo : **terminée en local**, commit sur `phase-0-fondations`
- **Prochaine action** : phase 1 — Backend socle (TDD : tests pytest d'abord).

### Critères de la phase 0 — vérité du terrain
| Critère | État |
|---|---|
| `docker compose up` démarre la base | ❌ **non vérifié** : Docker absent de cette machine (fichier `docker-compose.yml` écrit, image `postgres:18.6` tag vérifié sur Docker Hub) |
| CI s'exécute et passe | ⚠️ **non vérifié** : aucun remote GitHub configuré. Config YAML validée, commande gitleaks de la CI testée en local |
| gitleaks ne détecte rien | ✅ vérifié : `gitleaks dir .` + `gitleaks git --pre-commit --staged` → « no leaks found » |
| pre-commit passe | ✅ `pre-commit run --all-files` exit 0 |

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
