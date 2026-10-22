# Mirador (nom provisoire)

> SaaS de dashboard « en un coup d'œil » pour entreprises : finance, web analytics, réseaux sociaux, projets & tâches et identité légale, au même endroit.

> **Statut** : projet en cours de développement — **phases 0 à 6 livrées et mergées sur `main`** : fondations, auth & équipe, frontend socle & design system, connecteurs & données fictives, modules MVP (Finance, Web, Réseaux sociaux, Projets, Identité légale, vue d'ensemble « Pouls ») et fonctions transverses (comparaison de périodes, objectifs & budgets avec alerte de dérive, recherche globale Ctrl/Cmd+K, tableau de bord personnalisable, export PDF, notifications in-app, règles d'alerte, Web Push). **Prochaine étape : phase 7 « Mode démo »** (organisation `is_demo` isolée, scénarios sectoriels, `/demo` public et liens à durée limitée). Le détail par sous-phase est dans [`docs/PROGRESS.md`](docs/PROGRESS.md).

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
- **Phase 6 — Fonctions transverses** : 6a-i comparaison de périodes (`GET /organizations/{id}/metrics/{metric_key}/comparison` : deux fenêtres égales, agrégation par catalogue `sum`/`last`/`average`, `change`/`change_percent`) ; 6a-ii sélecteur de période 7 j / 30 j / 90 j sur la vue d'ensemble ; 6a-iii objectifs & budgets (table `goals` avec RLS, cible sur n'importe quel KPI, progression et alerte de dérive recalculées, endpoints `GET`/`POST`/`PATCH`/`DELETE /organizations/{id}/goals` gardés par le module de la métrique, audit `goal.created`/`updated`/`deleted`) ; **6a-iv panneau d'objectifs côté frontend** (liste, création/édition/suppression, progression et statut avec l'alerte de dérive en évidence, actions d'écriture selon le droit d'édition du module, i18n FR/EN) — **la sous-phase 6a est complète** ; **6b-i recherche globale (Ctrl/Cmd+K)** : bouton « Rechercher » (icône + `kbd`) dans la topbar, palette `SearchPalette` ouverte aussi par **Ctrl/Cmd+K** (Échap pour fermer, focus géré à l'ouverture/fermeture), index **frontend** des pages (modules visibles, Équipe réservée aux admins, paramètres) et des 8 KPI clés du Pouls (`KPI_META`, libellés i18n réutilisés) filtré par les permissions — un KPI mène à son module porteur, pas de backend ni de données d'API ; navigation flèches + Entrée ou clic, filtrage insensible à la casse et aux accents, i18n `search.*` FR/EN ; **6b-ii-a mise en page personnalisée du tableau de bord (backend)** : table tenant `dashboard_layouts` avec RLS (une ligne par couple organisation/utilisateur, contrainte d'unicité, disposition en JSONB), endpoints `GET`/`PUT`/`DELETE /organizations/{id}/dashboard` — le `GET` renvoie le catalogue des widgets autorisés (KPI des modules visibles, activité réservée aux admins) et la disposition enregistrée ou par défaut, le `PUT` remplace la disposition du membre (widget inconnu → 422, non autorisé → 403, doublon ou débordement de grille → 422), le `DELETE` restaure le défaut, audit `dashboard.layout.updated`/`reset` ; **6b-ii-b tableau de bord personnalisable côté frontend** : `react-grid-layout@2.3.0` (déplacement + redimensionnement, même grille 12 colonnes que le serveur), widgets du catalogue rendus par genre (`health`/`kpi`/`goals`/`activity`), bouton « Personnaliser » (mode édition : poignée de déplacement par widget, redimensionnement par le coin bas-droit, Enregistrer/Annuler/Réinitialiser, enregistrement par mutation et relecture), fil d'activité toujours réservé aux admins, i18n `dashboard.*` FR/EN — **la sous-phase 6b-ii est complète** ; **6c-i export PDF par l'impression du navigateur** : option `printable` de `PageHeader` (bouton « Exporter en PDF » + bandeau de document avec nom du produit, date de génération et période rappelée), feuille `@media print` qui masque l'interface, force le thème clair sur papier et n'imprime que le contenu — sur la vue d'ensemble, les modules Finance/Web/Réseaux sociaux/Projets et la fiche légale, i18n `print.*` FR/EN ; **6c-ii notifications in-app** : table tenant `notifications` (migration `f2f1e655c879`, RLS activée et forcée), une ligne par destinataire — `kind` (clé i18n, jamais un texte affiché), `params` JSONB, `link` (route du module) et `dedup_key` ; les événements **déjà** existants alimentent le canal (`goal.achieved`/`goal.off_track` évalués par le worker de synchro après l'écriture des métriques, `legal.diverged` au rafraîchissement du registre), pas encore de règle configurable (table `alert_rules` en 6c-iii) ; destinataires d'un objectif = administrateurs et membres ayant `edit` sur le module de la métrique, écart légal = administrateurs ; une seule non-lue par événement (une divergence qui dure met à jour sa notification) ; routes personnelles `GET /organizations/{id}/notifications` (page + `unread_count`) et `POST .../notifications/{id}/read` + `POST .../notifications/read-all` (204) filtrées par destinataire ; cloche de la barre supérieure avec badge de non-lus, panneau déroulant (fermeture au clic extérieur/Échap, élément menant à son module et se marquant lu), polling 5 min et i18n `notifications.*` FR/EN ; **6c-iii-a règles d'alerte configurables** : table tenant `alert_rules` (migration `0010`, RLS activée et forcée) — règle de **seuil** générique (clé canonique, sens `above`/`below`, seuil, fenêtre glissante 1–365 j, activation et libellé optionnel) dont la valeur est recalculée à la lecture (jamais stockée) ; endpoints `GET`/`POST`/`PATCH`/`DELETE /organizations/{id}/alert-rules` (lecture limitée aux modules visibles, écriture sous `edit` sur le module de la métrique, audit `alert_rule.*`) ; l'émission `alert.threshold` est réservée au worker de synchronisation (déduplication en base, destinataires = admins + membres en `edit` sur le module) ; panneau dans les paramètres (liste, création/édition, activation/désactivation, suppression, i18n `alertRules.*` FR/EN) et traduction du type `alert.threshold` dans le centre de notifications (reste 6c-iii-b : Web Push) ; **6c-iii-b notifications Web Push** : table tenant `push_subscriptions` (migration `0011`, RLS activée et forcée) — un abonnement **par navigateur** (`endpoint` unique, clés `p256dh`/`auth`, `user_agent`), l'abonnement est **personnel** (tout membre, aucun droit de module) ; l'application devient une **PWA** (`manifest.webmanifest`, `icon.svg`) servie par un **service worker** (`sw.js` : `push` + `notificationclick`, table FR/EN des `kind`) ; `app/services/push.py` porte l'interface `PushSender` (implémentée par `WebPushSender` — VAPID + `pywebpush` — et par un faux en test), l'envoi est **best-effort** au moment de chaque notification in-app (même `kind`/`params`/`link`, jamais de texte) via l'émetteur de `app.state.push_sender`, un endpoint caduc (404/410) est purgé ; routes `GET /organizations/{id}/push/public-key` (404 si non configuré), `POST`/`DELETE /organizations/{id}/push/subscriptions` ; réglage « Notifications hors onglet » dans les paramètres (`src/push/`), i18n `push.*` FR/EN — **la sous-phase 6c-iii est complète**.

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
