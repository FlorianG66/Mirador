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

## 2026-10-08 — Table `sessions` globale, jetons opaques hachés

Les sessions vivent dans une table globale sans RLS (comme `users`), pas du côté tenant. Raison : un utilisateur doit pouvoir se reconnecter avant d'appartenir à une organisation ; les jetons eux-mêmes sont des opaques aléatoires, seuls leurs hachages SHA-256 sont persistés, le refresh tourne à chaque usage et le logout révoque.

## 2026-10-08 — Sessions : Argon2id paramètres OWASP

`argon2-cffi==25.1.0` avec `m=19456, t=2, p=1` (recommandation OWASP) ; min 12 caractères via le schéma. Raison : le coût mémoire rend le cassage par lots impraticable sans changer les params du hash.

## 2026-10-08 — CSRF double submit sur une seule couche middleware

Un seul `SecurityMiddleware` pose les en-têtes de sécurité **et** refuse les écritures dont le cookie `mirador_csrf` diffère de l'en-tête `X-CSRF-Token` (comparaison à temps constant). Raison : une seule couche, rien à oublier route par route ; le CSRF n'est exigé que si un cookie d'authentification est joint (sinon une erreur 405 resterait un 403), et `/auth/register` et `/auth/login` restent exemptes.

## 2026-10-08 — Rate limit en mémoire (pas de Redis)

Chaque processus garde une fenêtre glissante par couple (route, IP) sur `app.state.rate_limiter`, 429 + `Retry-After`. Raison : proportionnel au besoin actuel (un seul processus de dev), mais à remplacer par un compteur partagé dès qu'un répartiteur ou plusieurs processus servent l'API (montée en charge).

## 2026-10-08 — Couverture : les lignes après `await` ne sont pas mesurées

coverage.py (testé `pytrace`, `ctrace`, `sysmon`) ne remonte pas les lignes exécutées juste après un `await` dans les coroutines du socle (SQLAlchemy async / FastAPI) : le code tourne pourtant (lignes vues par d'autres assertions), la mesure reste plancher. Raison : seuil de couverture conservé à 80 % (mesuré ~92 %), l'écart est documenté et chaque branche sensible a un test dédié — ne pas gonfler la couverture par des usines à gaz.

## 2026-10-08 — TOTP implémenté en interne, validé par les vecteurs RFC 6238

Pas de nouvelle dépendance : `app/core/totp.py` implémente RFC 6238 (HMAC-SHA1, 6 chiffres, période 30 s, tolérance d'un pas) en une vingtaine de lignes, testé contre l'appendice B officiel. Raison : le standard est stable et court, une bibliothèque de plus à surveiller n'est pas justifiée (AGENTS.md §2).

## 2026-10-08 — Secret TOTP stocké en clair au repos

`users.totp_secret` n'est pas chiffré en base ; le chiffrement (AES-GCM, clé maîtresse) arrive avec le module des identifiants d'outils tiers (SPEC §6). Raison : pas de clé maîtresse de chiffrement avant la phase des intégrations, et le secret volé ne suffit pas à se connecter (il faut aussi le mot de passe) ; l'A2F reste une protection forte contre le phishing et le vol de session.

## 2026-10-08 — Codes de secours hachés SHA-256, sans comparaison à coût élevé

Backup codes : 10 × 8 caractères (`ABCDEFGHJKLMNPQRSTUVWXYZ23456789`, sans caractères ambigus), stockés en base uniquement hachés SHA-256. Raison : leur entropie (≈ 40 bits) plus le rate limiting de `verify` excluent la force brute ; Argon2 serait un surcoût inutile sur une table dédiée.

## 2026-10-08 — Défi A2F à usage unique, cookie dédié

Connexion avec TOTP actif : aucun cookie de session, un cookie `mirador_2fa` (httpOnly, `Path=/api/v1/auth`, 5 min) et une ligne `auth_challenges` (jeton opaque haché) ; `verify` échange le défi contre une session complète puis le consomme. Raison : le cookie de défi ne porte aucun privilège, il est limité à la route de vérification ; la ligne consommée bloque le rejeu.

## 2026-10-08 — Jeton de réinitialisation : 30 min, à usage unique, révocation des sessions

`password_reset_tokens` : jeton opaque haché, expiration 30 min, consommé à l'usage ; le reset change le mot de passe et révoque toutes les sessions du compte. Raison : un lien capté doit expirer vite et ne servir qu'une fois ; toute session ouverte ailleurs doit mourir (mot de passe == nouveau).

## 2026-10-08 — E-mails journalisés jusqu'au SMTP (phase 11)

Interface `EmailSender` + `LogEmailSender` sur `app.state.email_sender`, remplacée par de vrais e-mails seulement à la phase 11. Raison : sans SMTP, le lien de reset doit rester visible en dev ; l'interface permet aux tests d'injecter un faux émetteur sans toucher aux routes.

## 2026-10-08 — `forgot`/`reset`/`verify` sans CSRF quand anonyme, protégés sinon

`auth/password/*` et `auth/2fa/verify` sont exemptés de la vérification CSRF seulement quand aucun cookie d'authentification n'est joint (l'utilisateur vient de la page de connexion) ; s'ils arrivent avec une session, la protection s'applique. Raison : pas de CSRF à fournir depuis la page publique, mais une attaque depuis un site tiers ne doit jamais pouvoir agir sur un compte connecté.

## 2026-10-08 — Le lien d'invitation porte l'organisation

Le lien contient le jeton **et** l'organisation (`/invitations/accept?token=…&organization=…`) ; `accept` pose le tenant avant de lire l'invitation. Raison : la table `invitations` est sous RLS, sans GUC tenant la ligne est invisible, et le seul jeton ne dit pas dans quelle organisation on entre.

## 2026-10-08 — `none` n'est jamais stocké

Seules les lignes `view` et `edit` sont écrites ; l'absence de ligne vaut `none`, et la réponse API affiche toujours les cinq modules (l'admin a `edit` partout sans ligne). Raison : évite un état redondant susceptible de contredire l'absence de ligne, et rend la lecture d'une fiche simple (une ligne par module accordé).

## 2026-10-08 — Erreurs métier levées par les services (`ServiceProblem`)

Les services lèvent `ServiceProblem(status_code, detail)` ; le handler global la convertit en RFC 9457, les routes ne font aucun `try/except`. Raison : messages figés au même endroit, testés à l'unité comme via l'API, et la logique reste dans `services` (AGENTS.md §4).

## 2026-10-08 — Auto-révocation interdite

Un admin ne peut ni retirer ses propres permissions ni se révoquer lui-même (400). Raison : sinon l'organisation peut se retrouver sans aucun administrateur, et personne n'est alors plus habilité à la récupérer.

## 2026-10-08 — Clusters de test PostgreSQL détruits (`cleanup_mode="delete"`)

Le `conftest` crée un cluster pgserver par session avec `cleanup_mode="delete"` (au lieu du défaut `stop`, qui ne fait que l'arrêter). Raison : chaque session laissait ~50 Mo dans `%TEMP%`, ce qui a fait tomber le disque en plein milieu de phase ; le répertoire est de toute façon recréé à chaque run.

## 2026-10-08 — Google ne crée jamais de compte

`authenticate_google` ne relie l'identité Google qu'à un **compte existant** (e-mail non vérifié → 403, aucun compte → 403). Raison : créer un compte depuis un e-mail imposerait d'inventer un nom d'organisation et contournerait les invitations (2d) ; la création automatique sera arbitrée à une phase ultérieure si le besoin se confirme.

## 2026-10-08 — Identité Google via userinfo, sans vérification JWT locale

Échange du code en HTTPS (`client_secret`) puis appel au userinfo pour l'identité : aucune dépendance crypto ni vérification de signature côté backend. Raison : `httpx` (déjà épinglé `0.28.1` en dev) est promu dépendance runtime, et Google reste la seule source de vérité sur l'e-mail vérifié.

## 2026-10-08 — État OAuth en cookie httpOnly comparé à temps constant

L'état vit dans `mirador_oauth_state` (httpOnly, `SameSite=lax`, 10 min, `Path=/api/v1/auth`), comparé au paramètre `state` via `hmac.compare_digest`, effacé au succès du callback. Raison : le frontend n'a jamais besoin de le lire, et un état lisible ou persistant exposerait la protection CSRF du parcours (RFC 6749 §10.12).

## 2026-10-08 — L'A2F TOTP reste exigée après Google

Un callback Google sur un compte à TOTP actif délivre le défi `mirador_2fa` (comme le login e-mail/mot de passe), jamais une session directe. Raison : sinon la connexion Google contournerait le second facteur — l'A2F protège le compte, pas la méthode d'entrée.

## 2026-10-08 — URI de retour Google dérivée de `app_base_url`

`Settings.google_redirect_uri = app_base_url + /api/v1/auth/google/callback`, sans setting dédié. Raison : une seule origine (frontend + API) est supposée, à enregistrer à l'identique dans la console Google ; si les domaines divergent, un setting dédié sera ajouté alors (pas de configuration prématurée).

## 2026-10-08 — Échec du fournisseur OIDC : 502 dédié

`OidcProviderError` a son propre handler global : message figé « Connexion Google impossible. », détail technique au journal uniquement. Raison : sans handler, l'exception remonterait en 500 générique sans trace exploitable, et un message repris de Google exposerait le détail d'un tiers (ASVS L2).

## 2026-10-08 — Frontend épinglé : TypeScript 5.9, pas la « latest » 7

`typescript@7.0.2` est « latest » sur npm mais `typescript-eslint@8.71.1` n'accepte que `typescript < 6.1.0` : on épingle `5.9.3` (dernière 5.x), et on remontera quand le plugin la supportera. Raison : un lint TypeScript est impossible avec TS 7 aujourd'hui ; toutes les versions frontend sont d'ailleurs épinglées exactement (pas de caret).

## 2026-10-08 — Proxy Vite `/api` en dev, pas de CORS

`vite.config.ts` proxifie `/api/*` vers `127.0.0.1:8000` ; le navigateur reste same-origin. Raison : le client API (3c) appellera `/api/v1` sans base URL à configurer, et la règle CORS du backend reste limitée à ce qui sert vraiment en prod.

## 2026-10-08 — Règles React Hooks épinglées par nom

ESLint embarque `eslint-plugin-react-hooks` avec `rules-of-hooks` (error) et `exhaustive-deps` (warn) déclarés nommément, et non via `configs.recommended` (dont la clé et le contenu varient entre versions du plugin). Raison : lint stable indépendamment des évolutions du plugin (v7 change ses bundles).

## 2026-10-09 — Tailwind CSS v4, design tokens en variables CSS

`tailwindcss` + `@tailwindcss/vite` 4.3.3 ; couleurs et rayons sont des variables CSS (`:root`/`.dark`) exposées à Tailwind par `@theme inline`, les composants n'utilisent que des tokens sémantiques. Raison : SPEC §7 veut des tokens pour un clair/sombre et un futur branding triviaux ; Tailwind v4 s'intègre au plugin Vite, sans `tailwind.config`.

## 2026-10-09 — Primitives maison plutôt que shadcn/ui à ce stade

Les composants de base (Button, Card, KpiCard, ChartCard, Skeleton, EmptyState, ErrorState) sont écrits en tokens avec `clsx` + `tailwind-merge` (pattern shadcn), sans installer shadcn/ui. Raison : les primitives de la phase 3b sont simples ; shadcn/ui sera adopté quand des composants accessibles non triviaux (dialogue, combobox, menu) seront requis (pages 3d et suivantes), plutôt que de copier du code à l'avance.

## 2026-10-09 — React Router, i18next, lucide-react, motion

`react-router` 8.4.0 (routing client), `i18next` + `react-i18next` (FR défaut, EN ; `initAsync:false`), `lucide-react` (icônes) et `motion` (transitions). Raison : librairies citées par SPEC §5.2 ; `motion` n'est utilisé que pour les transitions de page, la logique d'animation (compteurs) restant en `requestAnimationFrame`. Toutes les autres dépendances ajoutées en 3b (`clsx`, `tailwind-merge`, `@tailwindcss/vite`, `tailwindcss`) servent les tokens et le style.

## 2026-10-09 — Amorçage du thème avant le premier rendu

Un script inline dans `index.html` pose la classe `.dark` depuis `localStorage` (`mirador-theme`) avant le rendu, avec la même logique que le hook `useTheme`, stockage protégé (navigation privée). Raison : éviter un flash de thème inversé au chargement. Une CSP stricte (phase 11) nécessitera un nonce ou un script externe.

## 2026-10-09 — Bundle frontend non gzippé > 500 kB assumé à ce stade

`npm run build` dépasse le seuil d'avertissement Vite (≈ 531 kB, ≈ 169 kB gzip) à cause de React + Router + Motion + i18next. Raison : acceptable pour un dashboard derrière login ; le découpage de code (routes paresseuses, chunks vendeurs) viendra avec les pages réelles (3c/3d, phase 5), pas en avance.

## 2026-10-09 — Client API typé généré depuis l'OpenAPI

`backend/scripts/export_openapi.py` sérialise le schéma (`create_app().openapi()`) vers `frontend/openapi/schema.json` (commité : il rend les changements d'API visibles dans les diffs) ; `openapi-typescript@7.13.0` en génère `src/api/schema.d.ts` via le script npm `generate:api` (fichier généré, exclu d'ESLint). Les appels passent par `openapi-fetch@0.17.0` (`src/api/client.ts`). Raison : un seul contrat typé de bout en bout, sans maintenir un client complet à la main ; le schéma est régénéré quand l'API change.

## 2026-10-09 — CSRF double submit répliqué côté client

`src/api/client.ts` recopie le cookie `mirador_csrf` dans l'en-tête `x-csrf-token` pour toute méthode non sûre (POST/PUT/PATCH/DELETE), jamais pour GET/HEAD/OPTIONS. Raison : le backend exige ce couple (2b) ; un middleware openapi-fetch évite tout oubli dans les appels.

## 2026-10-09 — Organisation active mémorisée dans `localStorage`

L'organisation active vit sous la clé `mirador.organizationId` : on garde l'id mémorisé s'il figure encore dans les memberships, sinon on retombe sur la première et on persiste. Raison : le sélecteur d'organisation n'existe pas encore, mais les permissions sont toujours lues pour une organisation précise.

## 2026-10-09 — Échec de `/auth/me` = anonyme, échec des permissions = erreur rechargeable

`/auth/me` en échec (401 ou réseau) donne l'état `anonymous` ; un échec de `/permissions` sur une session valide donne l'état `error` avec bouton de réessai. Raison : ne pas déconnecter pour une erreur transitoire, mais ne pas laisser croire non plus qu'il n'y a aucun droit.

## 2026-10-09 — Permission absente : page 403, pas redirection

`RequireModule`/`RequireAdmin` rendent `ForbiddenPage` quand le niveau vaut `none` ou que le rôle n'est pas admin ; seule l'absence de session redirige vers `/login`. Raison : rediriger un utilisateur connecté mais non autorisé boucle ou masque le problème ; un 403 explicite garde l'URL et reste honnête.

## 2026-10-09 — `baseUrl` = origine courante, `fetch` résolu à l'appel

`createClient` reçoit `baseUrl: window.location.origin` (front et API sous le même domaine : proxy en dev, reverse proxy en prod) et un `fetch` qui délègue à `globalThis.fetch` au moment de l'appel. Raison : une URL absolue est nécessaire (le client construit un `Request`), l'hypothèse same-origin rejoint celle de l'URI Google (2e), et les tests remplacent `fetch` via `vi.stubGlobal`.

## 2026-10-09 — Route « analytics » renommée « web »

Le backend et le schéma OpenAPI nomment ce module `web` ; le frontend utilisait `analytics`. Alignement sur `web` (route, clé i18n `nav.web`, widget du dashboard). Raison : une seule nomenclature module↔permission, la garde lit `permissions.modules[moduleKey]` avec la clé du schéma.

## 2026-10-09 — Refonte visuelle du frontend (« clair aéré », rail rétractable)

Direction retenue après revue des galeries d'inspiration (kombai, 5sdesign) : palette claire aérée type Linear/Notion, rail d'icônes rétractable (largeur pilotée par `--rail-w`, état mémorisé sous `mirador-rail-collapsed`), topbar riche (fil d'ariane, identité + rôle, langue, thème) et tableau de bord « bento » asymétrique (colonnes 7/5). Raison : refonte esthétique demandée en cours de phase 3, sans aucune donnée inventée (l'accès rapide pointe vers de vrais modules) ; ajouts purement présentationnels (tokens, `PageHeader`, `useRailCollapsed`, `lib/permissions.ts`), le contrat 3c et ses tests restent valides.

## 2026-10-09 — TanStack Query 5.104.1 pour le state management serveur

`@tanstack/react-query@5.104.1` (version stable npm vérifiée) remplace useState/useEffect dans `AuthProvider` et les mutations des formulaires. Configuration : `retry: false`, `refetchOnWindowFocus: false`. Les clés de query sont centralisées dans `src/auth/queries.ts` (`authKeys.me`, `authKeys.permissions(orgId)`). Raison : cache serveur partagé, invalidation déclarative (`reload()` = `invalidateQueries`), et intégration native avec les mutations des formulaires — sans ajouter de bibliothèque de formulaire (les formulaires restent contrôlés avec `useState`).

## 2026-10-09 — A2F : pages dédiées plutôt que modale

La double authentification utilise deux routes dédiées : `/2fa` (publique, défi après `totp_required` au login) et `/settings` (protégée, activation/désactivation TOTP). Raison : le défi 2FA est un flux à part entière (redirection depuis le login, cookie `mirador_2fa`), pas une simple modale ; la page paramètres centralise la gestion du compte sans surcharger le dashboard.

## 2026-10-10 — Seed des données fictives = 32 bits faibles de l'UUID d'organisation

`seed_for_organization(org_id) = org_id.int & 0xFFFFFFFF` produit les séries de démo de chaque organisation. Raison : déterminisme total (mêmes données à chaque synchro, tests stables) sans stocker de seed, et différenciation suffisante entre organisations de démo.

## 2026-10-10 — Re-synchronisation idempotente sur 365 jours, pas de « dernière synchro »

Le worker range/remplace les ~365 derniers jours à chaque passage (upsert sur `(organization_id, metric_key, captured_at)`), sans borne « dernière synchro » à tenir en base. Raison : il n'y a pas de vrai connecteur ni de volume avant la phase 9, et un recul dans l'historique reste toujours possible ; la montée en charge imposera une vraie borne.

## 2026-10-10 — Unité stockée par point de métrique (migration 0006)

`metric_snapshots.unit` est écrit à chaque point, pas seulement dans les métadonnées du connecteur. Raison : l'endpoint de lecture doit rester générique (il ignore quel connecteur a produit la série) et le format canonique (SPEC §5.4) porte une unité obligatoire.

## 2026-10-10 — Planificateur in-process, désactivé en test

Le worker tourne dans la boucle asyncio de l'application (lifespan, intervalle `SYNC_INTERVAL_MINUTES`, 0 = éteint), ni processus ni queue dédiés. Raison : un seul processus et des volumes de démo rendent un orchestrateur (APScheduler, Celery…) prématuré ; les tests httpx ne déclenchent pas le lifespan, donc rien ne tourne dans la CI.

## 2026-10-10 — Recharts 3.10.1 pour les graphiques (5a)

`recharts@3.10.1` (dernière version stable npm vérifiée, épinglée exactement, 0 vulnérabilité) est ajouté pour les graphiques du module Finance. Raison : SPEC §7 liste Recharts dans la stack ; les graphiques restent décoratifs (résumé `aria-label`), l'accessibilité des données passe par les KPI et listes textuelles.

## 2026-10-10 — Panneau finance = 8 clés canoniques fixes (5a)

Le frontend charge exactement 8 séries canoniques (`finance.revenue|expenses|margin|cash|budget|invoices_outstanding|top_clients|top_suppliers`), interrogées toutes ensemble (`Promise.all`, polling 5 min). Raison : une page dédiée consomme un contrat stable — pas de découverte dynamique de clés avant la phase 6 (dashboard personnalisable).

## 2026-10-10 — Série absente (404) = « module pas encore connecté » (5a)

Dans `fetchFinancePanel`, un 404 se traduit par une clé `missing` ; seule une clé **toujours** absente rend l'état vide de la page, une vraie erreur (réseau, 5xx, 403) affiche l'état d'erreur avec réessai. Raison : une organisation peut légitimement n'avoir aucune synchro du module, mais l'UI ne doit jamais masquer une panne.

## 2026-10-10 — Tops clients/fournisseurs : parts normalisées, noms fictifs (5a)

`finance.top_clients` vaut la somme du CA du jour avec `dimensions.top = [{name, amount}]` normalisé pour que les parts des noms additionnent 55 % (5 clients), `top_suppliers` 40 % (4 fournisseurs) — chiffres arbitrés comme « part représentée » réaliste. Raison : SPEČ §3 veut un top clients visible et la somme ≪ 100 % évite de prétendre l'exhaustivité ; les noms sont fictifs (jamais de vraies entreprises, dépôt public).

## 2026-10-10 — Marge brute peut être négative (5a)

`finance.margin = revenue − expenses` n'est pas bornée à 0 : un mauvais week-end donne une marge négative (test assoupli en conséquence). Raison : réalisme — une marge toujours positive casserait la cohérence visible entre les séries.

## 2026-10-10 — Trésorerie cumulée depuis l'époque, indépendante de la fenêtre (5a)

`finance.cash` cumule les flux journaliers nets depuis `CREATION_EPOCH` (constante du connecteur), quel que soit l'intervalle demandé. Raison : un « solde de trésorerie » ne peut pas dépendre de la fenêtre du widget — comme `social.followers`, il exige un cumul stable depuis l'origine.

## 2026-10-10 — Formatage affiché via `Intl.NumberFormat` (5a)

`src/metrics/format.ts` centralise devise, devise compacte et dates via `Intl` (langue active), jamais de formatage « à la main » dans les composants. Raison : FR et EN doivent produire les nombres et distances corrects (séparateurs, notation compacte) sans duplication.

## 2026-10-10 — Couleurs des graphiques = tokens de thème, pas de palette fixe (5a)

Les séries de `MultiSeriesChart` reçoivent des couleurs écrites en variables CSS (`var(--brand)`, `--danger`, `--warning`, `--success`). Raison : le clair/sombre bascule sans re-configurer les graphiques, et la charte reste contrôlée au seul endroit où sont définis les tokens.

## 2026-10-11 — Panneau web = 10 clés canoniques fixes (5b)

Le frontend charge exactement 10 séries (`web.sessions|visitors|pageviews|engagement_rate|avg_session_duration|conversions|traffic_sources|top_pages|devices|countries`), interrogées ensemble (`Promise.all`, polling 5 min). Raison : même contrat de page dédiée que la finance (5a) — colonne vertébrale `sessions`, pas de découverte dynamique de clés avant la phase 6.

## 2026-10-11 — Répartitions web : `dimensions.items` sommant la métrique parente (5b)

`web.traffic_sources`, `web.top_pages`, `web.devices` et `web.countries` portent `dimensions.items = [{name, value}]` trié décroissant, dont la somme vaut **exactement** la métrique parente (sessions, 60 % des pages vues, visiteurs, visiteurs). Raison : un widget de répartition ne doit pas contredire le KPI du dessus ; la dernière entrée absorbe l'arrondi.

## 2026-10-11 — Sources/appareils en clés canoniques, pays en codes ISO (5b)

Le connecteur stocke les sources (`direct`, `organic_search`, …) et appareils (`desktop`, `mobile`, `tablet`) comme clés canoniques traduites par i18n (`web.source.*`, `web.device.*`), et les pays comme codes ISO 3166-1 alpha-2 nommés côté UI via `Intl.DisplayNames`. Raison : aucun texte en dur dans les données (AGENTS.md §7), et l'affichage suit la langue active sans stocker de libellé.

## 2026-10-11 — `upsert_many` par lots (limite de paramètres asyncpg) (5b)

`metric_snapshots.upsert_many` découpe l'insertion en lots de 2 000 lignes (`_MAX_ROWS_PER_STATEMENT`) au lieu d'un unique `INSERT`. Raison : asyncpg refuse plus de 32 767 arguments par requête ; le module web (20 séries × 365 jours × 7 colonnes) dépassait la limite, un test de non-régression verrouille le découpage.

## 2026-10-11 — Formatage web centralisé dans `format.ts` (5b)

Compteurs (`formatInteger`, `formatPercent` sur ratio 0→1), durées (`formatDuration` : unités `minute`/`second` via `Intl.NumberFormat`) et pays (`formatCountry` via `Intl.DisplayNames`) rejoignent les formatages finance, sans aucun libellé d'unité codé en dur. Raison : FR/EN corrects et maintenus à un seul endroit, comme la décision 5a sur `Intl`.

## 2026-10-11 — Panneau social = 9 clés canoniques fixes (5c)

Le frontend charge exactement 9 séries (`social.followers|followers_growth|impressions|reach|engagements|engagement_rate|mentions|posts|top_posts`), interrogées ensemble (`Promise.all`, polling 5 min). Raison : même contrat de page dédiée que finance (5a) et web (5b) — colonne vertébrale `followers`, pas de découverte dynamique de clés avant la phase 6.

## 2026-10-11 — Abonnés cumulés depuis l'époque, croissance = variation positive (5c)

`social.followers` cumule depuis `CREATION_EPOCH` et reste monotone croissant ; `social.followers_growth` est la variation quotidienne du total (différence des points), donc **toujours ≥ 0**. Raison : un nombre d'abonnés ne baisse pas dans une démo crédible, et garder la croissance positive évite de relâcher l'assertion générique « espérance ≥ 0 » des séries (seule `finance.margin` y échappe).

## 2026-10-11 — Répartitions sociales : `dimensions.items` sommant la métrique parente (5c)

`social.followers` porte `dimensions.items = [{name, value}]` (abonnés par réseau, trié décroissant) sommant **exactement** le total, et `social.top_posts` porte les 4 meilleurs posts dont la somme vaut `engagements × 0.45` (`TOP_POSTS_SHARE`). Raison : cohérence visible avec les KPI du dessus (même principe qu'en 5b) ; les titres de posts sont fictifs (dépôt public) et 45 % évite de prétendre l'exhaustivité.

## 2026-10-11 — Réseaux stockés en clés canoniques, traduits par i18n (5c)

Le connecteur nomme les réseaux (`linkedin`, `instagram`, `facebook`, `x`, `youtube`) comme clés brutes, traduites côté UI par `social.network.*`. Raison : aucun texte en dur dans les données (AGENTS.md §7) et l'affichage suit la langue active ; `x` est affiché « X (Twitter) » sans stocker le libellé.

## 2026-10-11 — Panneau projets = 10 clés canoniques fixes (5d)

Le frontend charge exactement 10 séries (`projects.tasks_done|tasks_created|open_tasks|overdue_tasks|avg_completion_time|avg_progress|active_projects|tasks_by_status|person_load|upcoming_milestones`), interrogées ensemble (`Promise.all`, polling 5 min). Raison : même contrat de page dédiée que 5a/5b/5c — colonne vertébrale « stock de tâches ouvertes », pas de découverte dynamique de clés avant la phase 6 ; `tasks_created` complète `tasks_done` pour visualiser le rythme créées vs terminées qui alimente le stock.

## 2026-10-11 — Tâches ouvertes = stock cumulé, retards et répartitions en dérivent (5d)

`projects.open_tasks` est le cumul `INITIAL_BACKLOG + Σ(créées − terminées)` depuis `CREATION_EPOCH` (jamais négatif, indépendant de la fenêtre, comme `finance.cash`/`social.followers`) ; `overdue_tasks` (≤ stock), `tasks_by_status` et `person_load` en sont des fractions qui somment **exactement** le stock. Raison : un backlog de tâches est un état, pas un flux ; les widgets de répartition doivent rester cohérents avec le KPI d'ouvertes du dessus (même principe qu'en 5b/5c).

## 2026-10-11 — Jalons à venir = somme des jours restants, pas un compte (5d)

`projects.upcoming_milestones` porte `dimensions.items = [{name, value}]` où `value` est le nombre de jours restant jusqu'au jalon (jalons triés du plus proche au plus lointain) et la valeur de la série est la somme de ces délais. Raison : le widget `RankedList` affiche une intensité par jalon ; une somme de jours reste une métrique agrégée utile, là où un simple compte « 6 jalons » n'apporterait rien de plus que le nombre d'items.

## 2026-10-11 — Statuts et personnes en clés canoniques, traduits par i18n (5d)

Le connecteur nomme les 4 statuts (`todo`, `in_progress`, `review`, `blocked`) et les 6 personnes comme clés brutes, traduites côté UI par `projects.status.*` (les noms de personnes sont fictifs, aucun salarié réel — AGENTS.md §5). Raison : aucun texte en dur dans les données (AGENTS.md §7), l'affichage suit la langue active.

## 2026-10-11 — `mock.py` purgé du module projets, `sync` de base en erreur explicite (5d)

`MockProjectsConnector` et la clé `projects.tasks_done` quittent `mock.py` (le module a son panneau comme finance/web/social) et `MockConnector.sync` de base lève désormais `NotImplementedError` au lieu de retourner un stub. Raison : `mock.py` ne garde que les helpers partagés (`CREATION_EPOCH`, `MockMetricConfig`, `build_series`, `daily_value`, `cumulative_value`, `hash01`) ; un `sync` hérité par erreur doit échouer bruyamment plutôt que renvoyer des données muettes.

## 2026-10-11 — Découpage de la 5e en trois sous-phases (5e)

La 5e est scindée en **5e-a** socle backend (validation SIREN/SIRET/TVA + service de registre), **5e-b** persistance (`legal_profiles`/`legal_identifiers`, migration RLS) + endpoints `legal` + permission, **5e-c** page frontend `/legal`. Raison : la 5e couvre à elle seule validation, appel à des registres externes, nouveau schéma, endpoints et UI — trop pour une session (AGENTS.md §2 : découper si ça dépasse).

## 2026-10-11 — Registre légal : transport httpx injectable, jamais d'appel réel en CI (5e-a)

`RechercheEntreprisesRegistry` reçoit un `httpx.AsyncBaseTransport` (même schéma que `GoogleOidcProvider`) et un `sleep` injectables ; les tests fournissent un `httpx.MockTransport` à réponses simulées. Raison : la CI ne doit jamais dépendre d'un service public externe (ROADMAP 5e), et le backoff doit être testable sans attente réelle.

## 2026-10-11 — Modèle `LegalCompany` canonique, parsing tolérant et mapping à confirmer (5e-a)

Le registre produit une structure interne `LegalCompany`/`LegalLeader` indépendante du fournisseur ; `parse_recherche_entreprise` lit chaque champ de façon tolérante (absent → `None`) et masque dirigeants/adresse d'une entreprise non diffusible (`diffusable=False`). Le mapping (endpoint et noms de clés de l'API Recherche d'entreprises) est explicitement marqué « à confirmer sur la documentation officielle » avant production. Raison : ne rien deviner (AGENTS.md §2) ; un futur repli INSEE/pays doit produire la même structure.

## 2026-10-11 — Exception de la clé de Luhn (La Poste) documentée, non traitée (5e-a)

`is_valid_siret`/`is_valid_siren` appliquent la clé de Luhn standard ; l'exception connue (certains établissements de La Poste) n'est pas traitée. Raison : la règle exacte n'a pas été vérifiée sur une source officielle — mieux vaut un faux négatif documenté qu'une règle inventée (AGENTS.md §2).

## 2026-10-11 — Fiche légale : une table d'identité + une table d'identifiants (5e-b)

`legal_profiles` (1:1 avec l'organisation) porte les champs d'identité textuels et `legal_identifiers` (unique `organization_id, pays, schema`) porte les identifiants structurés, la TVA vivant ici sous `schema="vat"`, `pays="FR"`. Raison : la TVA est un identifiant calculé (pas un champ de saisie parmi d'autres) et la clé `(pays, schema)` prépare l'extension à d'autres pays/schémas sans migrer `legal_profiles`.

## 2026-10-11 — Provenance stockée par champ dans un JSONB `field_sources` (5e-b)

Chaque champ de la fiche légale a une entrée `field_sources[champ] = {source: "registry"|"manual", synced_at}`. Raison : l'UI doit afficher d'où vient chaque valeur et quand elle a été synchronisée (SPEC §3) ; un JSONB évite une table de provenance par champ pour un besoin purement informatif.

## 2026-10-11 — La saisie manuelle prime, l'écart avec le registre est journalisé (5e-b)

Lors d'un `refresh`, une valeur saisie à la main (`source="manual"`) n'est jamais écrasée par le registre ; si le registre renvoie une valeur différente, un audit `legal.profile.diverged` est consigné. Raison : une correction humaine est intentionnelle et ne doit pas être perdue par une resynchronisation ; l'écart reste traçable plutôt que silencieux.

## 2026-10-11 — Dirigeants et adresse masqués hors admin ; non-diffusable respecté (5e-b)

Les dirigeants ne sont exposés qu'à l'administrateur (`Role.ADMIN`) et, si l'entreprise est « non diffusible » au registre, adresse et dirigeants sortent masqués. Raison : données potentiellement personnelles (AGENTS.md §5) et exigence de l'annuaire des entreprises ; la même règle qu'en 5e-a est donc appliquée jusqu'à l'API.

## 2026-10-11 — `schema_name` côté Python, alias JSON `schema` (5e-b)

Le champ JSON `schema` de `LegalIdentifierOut` impose un attribut Python `schema_name` avec `serialization_alias="schema"`. Raison : `schema` entre en collision avec `BaseModel.schema` (déprécié mais résolu par Pydantic) ; l'alias préserve le contrat d'API attendu (`GET .../legal` renvoie `schema`).

## 2026-10-11 — Régénération OpenAPI différée à la 5e-c (5e-b)

L'export `frontend/openapi/schema.json` (donc `src/api/schema.d.ts`) n'est pas régénéré en 5e-b : il est couplé à l'écriture de la page frontend et sera produit une fois les endpoints figés par les tests. Raison : éviter deux régénérations pour un même contrat.

## 2026-10-11 — Page légale dans `src/legal/`, pas `src/metrics/` (5e-c)

La page `/legal` et son support vivent dans `src/legal/` (`queries.ts`, `mentions.ts`, `ProvenanceBadge.tsx`, `LegalEditForm.tsx`), hors du dossier `src/metrics/` des quatre autres modules. Raison : la fiche légale n'est pas un panneau de séries temporelles (pas de polling, un objet unique) ; garder ce dossier propre évite de mélanger deux contrats.

## 2026-10-11 — Export PDF via l'impression du navigateur (5e-c)

L'action « Exporter en PDF » appelle `window.print()` au lieu d'embarquer une bibliothèque de génération PDF. Raison : le navigateur produit un PDF correct sans dépendance supplémentaire (AGENTS.md §2 : option la plus simple) ; une vraie génération serveur sera arbitrée si un format imposé est requis.

## 2026-10-11 — Saisie manuelle : seuls les champs modifiés sont envoyés (5e-c)

Le formulaire compare la saisie à la fiche d'origine et n'envoie que les champs réellement modifiés ; un champ vidé n'est pas envoyé (le backend n'efface pas via `null`). Raison : préserver la provenance — un champ inchangé doit garder sa source `registry` et non basculer en `manual` ; l'effacement volontaire attendra un contrat dédié côté API.

## 2026-10-11 — Rafraîchissement : nombre de champs modifiés calculé côté client (5e-c)

Après un `POST /refresh`, l'UI compare la fiche avant/après et annonce « N champ(s) modifié(s) ». Raison : l'API ne renvoie pas d'indicateur de divergence dans la réponse (l'écart manuel est journalisé côté serveur) ; le delta visible suffit à informer sans exposer la mécanique d'audit.

## 2026-10-11 — Suppression de `src/pages/ModulePage.tsx` (5e-c)

Le placeholder `ModulePage` (quatre modules « en construction ») est supprimé une fois `/legal` remplacée par `LegalPage`. Raison : plus aucune route ne l'utilise — garder un fichier mort serait du bruit (contrôle de `git grep` avant suppression).

## 2026-10-12 — Pouls minimal : KPI clés + santé + activité, alertes et objectifs en phase 6 (5f)

Le Pouls livre un agrégat en lecture seule (KPI clés des modules autorisés, indicateur de santé, fil d'activité) et une carte « Objectifs » vide ; les règles d'alerte et d'objectif réelles arrivent en phase 6. Raison : décision de périmètre explicite (une sous-phase = un pas livrable) ; l'agrégat n'invente aucune règle métier.

## 2026-10-12 — La santé du Pouls est un signal d'exploitation, pas un jugement métier (5f)

`good`/`warning`/`unknown` ne dépend que de « un module visible a-t-il de la donnée ? » (`modules_with_data` / `modules_total`, légal exclu car sans métrique). Raison : aucune règle financière n'a été vérifiée (AGENTS.md §2 : ne rien deviner) — l'état reflète la connexion/synchro des modules, pas leur performance.

## 2026-10-12 — Le Pouls filtre par module autorisé, sans garde de module sur la route (5f)

La route `GET /organizations/{id}/pulse` n'a pas de garde de module : le service restreint lui-même chaque KPI aux modules visibles, et un membre sans module reçoit un Pouls vide (santé `unknown`), jamais un 403. Raison : la page d'accueil ne doit pas être un cul-de-sac pour un membre sans droit — elle affiche un état vide explicite.

## 2026-10-12 — Fil d'activité du Pouls réservé aux administrateurs (5f)

Le fil (journal d'audit, `services.audit.list_recent`) n'est renvoyé que si `membership.role == admin`, sinon la route l'omet (`activity: []`) et l'UI affiche une note « réservé aux admins ». Raison : ne pas contourner la règle de la 2d (audit admin-only) par la porte de l'agrégat.

## 2026-10-12 — Huit KPI clés, libellés de module réutilisés (5f)

Le Pouls expose 8 clés (2 par module à métrique) : `finance.revenue`/`margin`, `web.visitors`/`conversions`, `social.followers`/`engagement_rate`, `projects.open_tasks`/`avg_progress` ; le module légal n'a pas de métrique. Le frontend réutilise les libellés i18n existants des pages de module (`finance.*`, `web.*`, `social.*`, `projects.*`) et n'ajoute que `common.percent` et `web.kpiConversions`/`web.unitConversions`. Raison : une seule source de libellés (pas de duplication i18n), et aucune logique métier dans l'agrégat.

## 2026-10-12 — Lecture `get_latest` pour la valeur courante et la précédente (5f)

Le KPI du Pouls lit les deux derniers points via `metric_snapshots.get_latest` (tri décroissant), pas `get_series` (tri croissant, fenêtré). Raison : le Pouls veut la dernière valeur et la précédente pour la tendance, pas une série complète — une lecture dédiée est plus simple et évite de charger 365 points par KPI.

## 2026-10-12 — Comparaison de périodes calculée côté backend (6a-i)

L'agrégation d'une fenêtre et la frontière entre les deux périodes vivent dans `app/services/metrics.get_metric_comparison`, exposées par `GET /organizations/{id}/metrics/{metric_key}/comparison` ; le frontend ne fait qu'afficher. Raison : le même calcul resservira à la vue d'ensemble, à l'export PDF (6c) et au chatbot (phase 8) — une seule vérité testable plutôt qu'une règle dupliquée par page.

## 2026-10-12 — Catalogue d'agrégation `sum`/`last`/`average` par métrique (6a-i)

`app/services/metric_catalog.METRIC_AGGREGATIONS` classe chaque clé connue : flux → `sum`, niveau/stock → `last`, taux/durée → `average` ; une clé inconnue retombe sur `sum`. Raison : une série quotidienne peut être un flux (CA) ou un stock (trésorerie, abonnés) — sommer un stock n'a pas de sens. Un test exige que chaque métrique des quatre connecteurs soit classée (aucune omission silencieuse).

## 2026-10-12 — Comparaison : une lecture, frontière `end - days` (6a-i)

`get_metric_comparison` lit une seule fois la double fenêtre `[end - 2×days, end]` puis répartit les points (`captured_at > end - days` → période courante). Raison : une requête au lieu de deux, et une frontière déterministe (pas de point compté deux fois) facile à tester avec un `end` explicite ; le résumé expose `change` et `change_percent` (`null` si la période précédente vaut 0).
