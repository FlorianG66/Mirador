# AGENTS.md — Mirador (nom provisoire)

> Règles permanentes du projet. Lis ce fichier en entier au début de chaque session.
> Cahier des charges : `docs/SPEC.md`. Découpage en phases : `docs/ROADMAP.md`. Suivi : `docs/PROGRESS.md`.

## 1. Le projet en 3 lignes
SaaS de dashboard pour entreprises de tout secteur : il centralise finance, web analytics, réseaux sociaux, projets/tâches, identité légale de l'entreprise (puis d'autres modules) pour « jeter un coup d'œil » à ce qui se passe dans l'entreprise. Le dirigeant est admin et donne à chaque collaborateur l'accès aux modules de son choix. Projet perso : d'abord portfolio, objectif final = produit publiable et commercialisable.
Le nom est provisoire : utilise une constante `PROJECT_NAME` centralisée, jamais le nom en dur.
Le dépôt GitHub est **public** (portfolio) alors que le produit sera commercialisé : règles de dépôt public en §5, licence en SPEC §12. Fonction de base du produit : la fiche légale de l'entreprise (SPEC §3).

## 2. Méthode de travail
- **Une seule phase à la fois.** Quand on te dit « Phase N », lis uniquement la phase N dans `docs/ROADMAP.md` et les sections de `docs/SPEC.md` qu'elle référence. N'anticipe pas les phases suivantes.
- Commence par un plan court (/plan), puis exécute. Ne pose une question que si une ambiguïté bloque vraiment ou si une décision d'architecture majeure n'est couverte par aucun document.
- Décision non couverte ? Prends l'option la plus simple et maintenable, et note-la en 3 lignes dans `docs/DECISIONS.md` (date, décision, raison).
- Petits pas : fichiers courts (< 300 lignes), une responsabilité par fichier, commits atomiques. N'ouvre que les fichiers utiles, ne relis pas tout le repo.
- Si une phase risque de dépasser une session de travail, découpe-la en sous-phases (Na, Nb), commit à chaque sous-phase, et note dans `docs/PROGRESS.md` : phase en cours, dernière action, prochaine action. C'est ce qui permet de reprendre le lendemain.
- Si tu perds le fil : relis `AGENTS.md`, `docs/PROGRESS.md` et la phase en cours plutôt que de deviner.
- Versions : ne devine jamais une version. Vérifie la dernière version stable (PyPI / npm) avant d'installer, épingle-la, privilégie les librairies activement maintenues. Toute nouvelle dépendance est justifiée en une ligne dans `docs/DECISIONS.md`.
- Ne jamais inventer : si tu ne sais pas ou n'as pas pu vérifier quelque chose (API, option, comportement), dis-le. Ne prétends jamais qu'un test ou une commande a réussi sans l'avoir réellement exécuté.

## 3. Fin de phase (obligatoire, dans cet ordre)
1. Les tests de la phase sont écrits et **passent** (backend : pytest ; frontend : Vitest, et Playwright quand la phase le demande).
2. Lint, format et types passent (ruff, mypy, eslint, tsc) et la détection de secrets (gitleaks) ne trouve rien.
3. Documentation à jour : `README.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/PROGRESS.md`, `CHANGELOG.md`.
4. Commit en Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), puis push sur la branche `phase-N-nom`. Jamais de push avec des tests rouges. Demande-moi avant de merger sur `main`.
5. Récap en français : fait / pas fait / décisions prises / comment lancer et tester / prochaine phase.

## 4. Stack (détail et justification : SPEC §5)
- **Backend** : Python (dernière version stable supportée par les dépendances), FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic, PostgreSQL. Couches : `routers → services → repositories`. Aucune logique métier dans les routers.
- **Frontend** : React + TypeScript strict, Vite, React Router, TanStack Query, Tailwind CSS, shadcn/ui, Recharts, i18next, Motion (animations). Client API typé, généré depuis l'OpenAPI du backend.
- **Outillage** : Docker Compose (dev), pytest, ruff, mypy, Vitest, ESLint, pre-commit, GitHub Actions.

## 5. Sécurité & RGPD (non négociable)
- Aucun secret dans Git : `.env` ignoré, `.env.example` à jour.
- **Dépôt public** : tout ce qui est commité est visible de tous, pour toujours (l'historique Git aussi). Jamais de secret, de clé, de vraie donnée client ni de vrai identifiant (code, fixtures, logs, docs), ni de configuration d'infrastructure de production (dépôt privé séparé). Les données de démo sont toujours fictives et signalées comme telles. Un secret commité par erreur est compromis : on le révoque, on ne se contente pas de le supprimer.
- Dès la phase 0 : gitleaks en pre-commit et en CI, secret scanning + push protection GitHub, Dependabot, `SECURITY.md`, et licence (voir `LICENSE`, SPEC §12) en place **avant** le premier push public.
- Multi-tenant : chaque table métier porte `organization_id`, chaque requête est filtrée dessus, et PostgreSQL Row-Level Security est activé en défense en profondeur. Toujours tester qu'un tenant ne peut pas lire les données d'un autre.
- Mots de passe en Argon2id. Sessions par cookies httpOnly + Secure + SameSite, protection CSRF, rotation des refresh tokens. A2F TOTP et connexion Google (OIDC).
- Validation stricte des entrées (Pydantic), requêtes paramétrées uniquement, CORS restrictif, en-têtes de sécurité, rate limiting sur l'authentification.
- Identifiants des outils tiers chiffrés au repos. Logs sans données personnelles ni secrets. Journal d'audit des actions sensibles.
- RGPD : minimisation des données, export et suppression des données, durées de conservation définies.
- Référence : OWASP ASVS niveau 2. `pip-audit` et `npm audit` dans la CI.

## 6. Qualité & documentation
- Je dois pouvoir comprendre et maintenir ce code seul. Identifiants en **anglais** ; docstrings, commentaires et docs en **français**, qui expliquent le *pourquoi*, pas le *quoi*.
- Chaque module a un court en-tête qui explique son rôle ; les fonctions publiques ont une docstring.
- `README.md` (page GitHub) toujours à jour : présentation, fonctionnalités, prérequis, installation, lancement, tests, structure du repo, roadmap, licence.
- Tests : unitaires pour la logique, intégration pour l'API, un test de non-régression par bug corrigé.

## 7. Design (SPEC §7)
Moderne, arrondis, mode clair/sombre via variables CSS (design tokens), menu latéral gauche, effets « wow » soignés mais sobres (compteurs animés, transitions, skeleton loaders), `prefers-reduced-motion` respecté, accessibilité WCAG AA. **Aucun texte en dur** : tout passe par i18n (FR par défaut, EN).

## 8. Interdits
Pas de données en dur dans l'UI (tout vient de l'API, y compris les données fictives) ; pas de `any` TypeScript sans justification ; pas de debug commité ; pas de refactor hors périmètre de la phase.
