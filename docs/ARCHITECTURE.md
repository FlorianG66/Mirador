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
- **A2F / récupération (2c)** : TOTP RFC 6238 maison (`app/core/totp.py`, secrets 20 octets base32) + 10 codes de secours hachés SHA-256. Connexion avec TOTP actif → cookie `mirador_2fa` (5 min, confiné à `/api/v1/auth`) + défi `auth_challenges` à usage unique ; `POST /auth/2fa/verify` l'échange contre une session. Réactivation régénère secret et codes ; désactivation exige le mot de passe courant. `POST /auth/password/forgot` (réponse invariante, anti-énumération) émet un jeton 30 min haché à usage unique (`password_reset_tokens`) ; `POST /auth/password/reset` change le mot de passe et révoque toutes les sessions. E-mails via `EmailSender` (`LogEmailSender` en dev, SMTP à la phase 11), lien construit sur `Settings.app_base_url`.
- **Invitations, équipe, audit (2d)** : `POST /organizations/{id}/invitations` (admin seul, rate limit `invite` 10/h, TTL 7 j, e-mail via `EmailSender`) crée une ligne `invitations` et journalise `invitation.created` ; le lien porté par l'e-mail contient le jeton **et** l'organisation. `POST /auth/invitations/accept` (compte authentifié dont l'e-mail correspond — 401 absent/expiré, 403 e-mail différent, 409 déjà membre) pose le tenant avant de lire l'invitation, crée le membre, écrit les permissions et journalise `invitation.accepted`. `DELETE …/invitations/{id}` révoque. Équipe : `GET /organizations/{id}/members`, `GET /permissions` (les cinq modules, `none` = absence de ligne, admin = `edit` partout), `PATCH /members/{user_id}/permissions` (audit `membership.permissions.updated` avec avant/après), `DELETE /members/{user_id}` (`membership.revoked`, auto-révocation refusée), `GET /audit-logs`. Les services lèvent `ServiceProblem` (erreurs RFC 9457 via handler global), les routes sans `try/except`.
- **Connexion Google (2e)** : `GET /auth/google` génère un état opaque, le range dans un cookie `mirador_oauth_state` (httpOnly, `SameSite=lax`, 10 min, `Path=/api/v1/auth`) et renvoie l'URL d'autorisation ; `GET /auth/google/callback` compare l'état au paramètre reçu (comparaison à temps constant), échange le code contre une identité via `app.state.oidc_provider` (`GoogleOidcProvider` : jeton puis userinfo en HTTPS, sans vérification locale de JWT), puis session classique — ou défi A2F si le TOTP est actif. Jamais de création de compte : e-mail Google non vérifié → 403, aucun compte à cet e-mail → 403. Fournisseur absent (identifiants absents) → 404 ; échec du fournisseur → 502 avec message figé (détail technique au journal seulement). Identifiants via `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`, URI de retour dérivée de `Settings.app_base_url`.
- **Sécurité transverse** (`app/core/middleware.py`) : en-têtes de sécurité sur toutes les réponses et CSRF double submit — le cookie `mirador_csrf` doit être repris dans l'en-tête `X-CSRF-Token`, exigé seulement pour les écritures **avec** cookie d'authentification (le 405 d'une route inconnue reste un 405) ; `/auth/register`, `/auth/login` et les routes d'usage anonyme (`/auth/password/*`, `/auth/2fa/verify`) ne l'exigent pas quand il n'y a pas de session jointe.
- **Rate limit** (`app/core/rate_limit.py`) : fenêtre glissante en mémoire par couple (route, IP) sur `app.state.rate_limiter`, 429 + `Retry-After` au-delà du quota ; quotas — `login`, `register`, `verify-2fa` 5/min, `forgot` 3/15 min, `reset` 5/h, `invite` 10/h, `google` 10/min (démarrage + callback partagés) ; un répartiteur ou plusieurs processus devront partager un compteur (v. `DECISIONS.md`).

- **API** : préfixe `/api/v1` ; `/health` (vivacité, sans base) et `/health/db` (200 si PostgreSQL répond, 503 en `application/problem+json` sinon).
- **Erreurs** : handlers globaux (404, 405, 422, 500) au format RFC 9457, titres = phrases HTTP ; jamais d'erreur 500 brute ni de fuite de détail.
- **Logging** : handler unique JSON sur le logger `app` (tous les modules `app.*` y propagent), `propagate=False`, idempotent.
- **Config** : `Settings` (env → `.env`), URL forcée en `postgresql+asyncpg://` ; les settings sont portés par `app.state` et injectés en test via `create_app`.
- **Migrations** : Alembic async (`alembic/env.py` lit les settings), baseline `0001` + `0002` (6 tables phase 2 et RLS) + `0003` (table `sessions`) + `0004` (A2F : colonnes `totp_*` sur `users`, tables `auth_challenges`, `backup_codes`, `password_reset_tokens`, hors RLS).
- **Tests** : `pgserver` lance PostgreSQL 16.2 éphémère pour les tests (CI incluse, sans Docker), cluster détruit en fin de session (`cleanup_mode="delete"` — sinon ~50 Mo laissés dans le répertoire temporaire par exécution) ; seuil de couverture 80 % ; base vidée avant chaque test (isolation des e-mails uniques).

## Structure frontend

SPA React (Vite) derrière login : pas de SSR (le backend est déjà FastAPI). Client API généré depuis l'OpenAPI (phase 3c). Voir `SPEC.md` §5.2.

```
frontend/
  index.html            entrée HTML ; script d'amorçage du thème (classe .dark avant le premier rendu)
  vite.config.ts        Vite (React + Tailwind v4) + proxy /api → 127.0.0.1:8000 + config Vitest
  eslint.config.js      ESLint flat (JS + TS typé + règles React Hooks + react-refresh)
  tsconfig*.json        TypeScript strict, build par incréments (app + node)
  src/
    main.tsx            montage React, document.title = PROJECT_NAME, import de l'i18n
    App.tsx             routeur (createBrowserRouter) sur la table de routes
    app/routes.tsx      table des routes (AuthProvider > RequireAuth > AppShell + gardes par module)
    api/                client typé : schema.d.ts (généré), client.ts (CSRF/ApiError), types.ts
    auth/               context.ts (useAuth), AuthProvider.tsx, guards.tsx (RequireAuth/Module/Admin)
    components/
      layout/           AppShell (menu latéral + topbar), Sidebar, SidebarNavItem,
                        Topbar, ThemeToggle, LanguageSwitcher, PageTransition
      ui/               design system : Button, Card, PageHeader, KpiCard, ChartCard,
                        Skeleton, EmptyState, ErrorState, button-variants
    pages/              DashboardPage, ModulePage, LoginPage, RegisterPage, ForgotPasswordPage,
                        ResetPasswordPage, TwoFactorPage, SettingsPage, TeamPage, ForbiddenPage, NotFoundPage
    hooks/              useTheme (clair/sombre), usePrefersReducedMotion, useCountUp, useRailCollapsed
    i18n/               instance i18next (FR défaut, EN) + locales fr/en
    lib/utils.ts        cn() = clsx + tailwind-merge
    lib/permissions.ts   canSeeModule (filtrage des modules par permission)
    constants.ts        PROJECT_NAME centralisé (AGENTS.md §1)
    index.css           design tokens (variables CSS) + mapping @theme inline (Tailwind v4)
    test/setup.ts       Vitest : matchers jest-dom + i18n + nettoyage du DOM
```

- **Design system (3b)** : couleurs et rayons en variables CSS (`:root` clair, `.dark` sombre) exposées à Tailwind par `@theme inline` ; les composants n'utilisent que des tokens sémantiques (`bg-surface`, `text-muted`, `text-danger`…). Thème piloté par la classe `.dark` sur `<html>` (hook `useTheme`, préférence dans `localStorage` ; `prefers-color-scheme` seulement à la première visite), amorcé par un script inline pour éviter le flash.
- **Layout** : `AppShell` = rail rétractable gauche (`useRailCollapsed`, largeur `--rail-w`) + topbar + contenu ; sur mobile le menu coulisse (overlay, fermeture par Échap). Lien d'évitement vers le contenu et `aria-current` actif sur la navigation (WCAG AA). `PageHeader` = en-tête de page partagé (titre + description).
- **i18n** : aucun texte en dur (AGENTS.md §7) ; ressources FR/EN embarquées, `initAsync:false` (init synchrone), `<html lang>` suit la langue active.
- **Animations** : transitions de page via Motion (fondu + glissement), compteurs animés via `requestAnimationFrame` ; toutes neutralisées si `prefers-reduced-motion: reduce`.
- **Routing** : React Router ; les routes de modules sont des placeholders à états vides, sans données en dur (AGENTS.md §8), en attendant l'API et les pages réelles (3c/3d, phase 5).

- **Client API (3c)** : `backend/scripts/export_openapi.py` exporte le schéma (`create_app().openapi()`) vers `frontend/openapi/schema.json` (commité) ; `openapi-typescript` en génère `src/api/schema.d.ts` (script npm `generate:api`, exclu d'ESLint) ; les appels passent par `openapi-fetch` (`src/api/client.ts`, `baseUrl` = origine courante, cookies inclus). Un middleware ajoute `x-csrf-token` (copie du cookie `mirador_csrf`) sur les méthodes non sûres ; un échec HTTP devient `ApiError` (RFC 9457) ; `unwrap` renvoie les données ou lève.
- **2FA (3d-b)** : route publique `/2fa` (défi après `totp_required` au login, `POST /auth/2fa/verify`) ; route protégée `/settings` (activation `POST /auth/2fa/enable`, désactivation `POST /auth/2fa/disable`) ; lien Paramètres dans la sidebar.
- **TanStack Query (3d-a)** : `@tanstack/react-query@5.104.1` — `QueryClientProvider` dans `main.tsx` (retry false, refetchOnWindowFocus false). `AuthProvider` utilise `useQuery` pour `/auth/me` (clé `authKeys.me`) et les permissions (clé `authKeys.permissions` orgId) ; `reload()` = `invalidateQueries({ queryKey: authKeys.me })`. Les formulaires (login, inscription, forgot/reset password) utilisent `useMutation` de TanStack Query avec `unwrap` du client API.
- **Auth & gardes (3c)** : `AuthProvider` charge `/auth/me` puis les permissions de l'organisation active (mémorisée dans `localStorage`, sinon la première) ; états `loading`/`anonymous`/`authenticated`/`error`. `RequireAuth` redirige vers `/login` si non connecté ; `RequireModule` et `RequireAdmin` rendent `ForbiddenPage` (403) faute de droits ; le menu latéral filtre les modules visibles (un admin voit tout, `Équipe` lui est réservée).Qualité frontend : `npm run lint` (ESLint, aussi en hook pre-commit), `npm run typecheck` (`tsc -b`), `npm test` (Vitest, environnement jsdom), `npm run build` (`tsc -b && vite build` ; bundle non gzippé > 500 kB à ce stade, v. `DECISIONS.md`). En dev, le backend doit tourner sur `127.0.0.1:8000` (uvicorn) et le navigateur ouvre `http://localhost:5173`.

## Environnements

- **Dev** : Docker Compose (PostgreSQL avec volume persistant), `.env.example` en modèle.
- **CI** : lint (ruff, eslint), types (mypy, tsc), tests (pytest, Vitest), gitleaks, audit des dépendances.
- **Production** : PaaS managé français (voir `SPEC.md` §10), config d'infra dans un dépôt privé séparé.
