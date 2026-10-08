# Décisions d'architecture

Journal des décisions non couvertes par `SPEC.md` / `ROADMAP.md` (format : date, décision, raison — 3 lignes max).

## 2026-10-07 — Emplacement des documents

Les documents sont à la racine du dépôt (`SPEC.md`, `ROADMAP.md`) et non dans `docs/`, comme initialisés par le projet ; `docs/` accueille ARCHITECTURE, DECISIONS, PROGRESS. Raison : ne pas déplacer les fichiers déjà référencés, la racine reste lisible sur GitHub.

## 2026-10-07 — Images PostgreSQL épinglées

`postgres:18.6` dans le Docker Compose (tag vérifié sur Docker Hub). Raison : jamais de version devinée, reproductibilité ; mise à jour explicite.

## 2026-10-07 — Hook eslint différé à la phase 3

pre-commit embarque ruff + gitleaks + pre-commit-hooks dès la phase 0 ; le hook eslint cible déjà les fichiers `frontend/` mais ne s'exécutera qu'à la phase 3 (le frontend n'existe pas encore, `npm run lint` sera défini alors). Raison : un hook système sans `package.json` ferait échouer `pre-commit run --all-files` aujourd'hui.

## 2026-10-07 — Base de test sans PostgreSQL local *(obsolète → voir « pgserver » ci-dessous)*

Cette machine n'a ni Docker ni PostgreSQL : la couche base (phase 1) est écrite pour PostgreSQL/asyncpg mais les tests de connexion ne peuvent pas tourner ici. Raison : pas de mensonge sur l'état des tests ; à exécuter dès que la base est disponible (CI ou machine avec Docker).

## 2026-10-07 — Tests de base via pgserver

`pgserver==0.1.4` (wheel épinglée, binaires PostgreSQL 16.2 fournis) lance une vraie base PostgreSQL éphémère en TCP pour les tests — sans Docker ni service externe. Raison : elle remplace la décision « non vérifiable » ci-dessus ; les tests de connexion/health sont réellement exécutés et verts.

## 2026-10-07 — Application créée par fabrique, settings portés par l'app

`create_app(settings=None)` au lieu d'un objet `app` au niveau module ; les settings vivent sur `app.state.settings` et sont injectés en test via les paramètres de `create_app`. Raison : aucun import déclencheur de config, et les tests changent d'URL de base sans variables d'environnement globales.

## 2026-10-07 — RLS sur les tables tenant uniquement

`memberships`, `module_permissions`, `invitations`, `audit_logs` portent `organization_id` et la RLS activée + forcée ; `users` et `organizations` restent des tables d'identité globales sans RLS. Raison : un utilisateur et une organisation existent avant d'appartenir à un tenant, leur isolation se joue par les memberships (AGENTS.md §5).

## 2026-10-07 — Une seule politique RLS par table, `WITH CHECK` plus restrictif

`USING` lit l'organisation **ou** l'utilisateur courant (un membre voit ses rattachements avant de connaître l'organisation active) ; `WITH CHECK` n'accepte que l'organisation courante. Raison : sinon un utilisateur pourrait s'insérer lui-même dans n'importe quelle organisation — escalade de privilèges. Le compte de politiques est fixé à 4 par les tests.

## 2026-10-07 — Tests d'isolation en rôle non-superuser

PostgreSQL contourne toujours la RLS pour un superuser (`FORCE` ne vise que le propriétaire de table) : les fixtures créent `mirador_test` (LOGIN, `GRANT` sur le schéma public) et l'application de test s'y connecte. Raison : vérifié sur le terrain, sinon les tests d'isolation passeraient à vide.

## 2026-10-07 — E-mail normalisé dans le repository

`users.create_user` / `get_user_by_email` convertissent en minuscules avant écriture et lecture. Raison : la contrainte `users_email_lowercase` et l'index unique l'exigent, et l'authentification par e-mail doit être insensible à la casse quel que soit l'appelant.
