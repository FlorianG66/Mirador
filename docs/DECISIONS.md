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
