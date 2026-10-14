# Progression

> Fichier de reprise : si tu perds le fil, lis `AGENTS.md`, ce fichier, puis la phase en cours dans `ROADMAP.md`.

## État

- **Phase en cours** : 6 — Fonctions transverses (ROADMAP ligne 58, réf. SPEC §4). Les sous-phases **6a, 6b-i, 6b-ii-a et 6b-ii-b sont complètes** (voir Historique) : 6a-i `4c41e9e`, 6a-ii `01c2220`, 6a-iii `831546e`, 6a-iv `e114627`, 6b-i recherche globale `bd6dcbf`, 6b-ii-a persistance de la mise en page (backend) `3f26777`, **6b-ii-b tableau de bord personnalisable (frontend)**. Prochaine brique : **6c** notifications (in-app + Web Push) + export PDF. La phase 5 est clôturée et mergée sur `main` (5a → 5f, merge `dcb7c9d`).
- **Branche** : `phase-6-transverse` (créée depuis `main` = `4c1b221` ; la phase 5 reste sur `main`/`phase-5-modules-mvp`) — 6a-i `4c41e9e`, 6a-ii `01c2220`, 6a-iii `831546e`, 6a-iv `e114627`, 6b-i `bd6dcbf`, 6b-ii-a `3f26777`.
- **Prochaine action** : 6c — notifications in-app + Web Push et export PDF (SPEC §4).
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

### Critères de la phase 2b — vérité du terrain
| Critère | État |
|---|---|
| Tests écrits d'abord (RED) puis GREEN | ✅ RED avant toute implémentation : **44 failed / 52 passed** ; GREEN : **98 passed** |
| pytest vert | ✅ `pytest --cov=app` → 98 passed |
| Couverture ≥ 80 % | ✅ **92 % mesurés** (le manque restant est un artefact coverage sur les coroutines, voir `DECISIONS.md`) |
| ruff check + format | ✅ exit 0 / 61 fichiers conformes |
| mypy strict | ✅ 0 erreur sur 38 fichiers |
| Migration Alembic `0003` (sessions) | ✅ aller-retour `head → base` vérifié sur base jetable, table sans RLS |
| Anti-énumération | ✅ message unique `Identifiants incorrects.` + vérification d'un hachage factice |
| CSRF | ✅ 403 sans jeton / jeton faux, exemptes register+login, un 405 reste un 405 |
| Rate limit | ✅ 429 + `Retry-After`, login et register comptés séparément |
| Cookies | ✅ httpOnly, `SameSite=lax`, paths respectifs, `Secure` en production |
| pre-commit passe | ✅ `pre-commit run --all-files` → 10 hooks Passed |
| gitleaks ne détecte rien | ✅ passé dans pre-commit |
| CI backend | ⚠️ job écrit, **non exécuté** (aucun remote GitHub) |

### Pièges rencontrés en phase 2b (à ne pas re-piocher)
- **Les tests HTTP commitent** : la base de test est partagée et l'inscription est persistante → deux tests avec le même e-mail se marchaient dessus. Corrige par un `TRUNCATE ... CASCADE` autouse avant chaque test (`clean_tables`).
- **Response injectée × Response retournée** : une `Response` injectée par FastAPI a `status_code=None` ; la retourner telle quelle casse la réponse. Pour un 204, construire explicitement une `Response(status_code=204)` et poser les cookies dessus.
- **`Response.headers` injectée ≠ mergée si on retourne une Response** : FastAPI ne recopie les en-têtes de la Response injectée que dans le cas « développement de la réponse » (retour de modèle). En retournant une Response, tout passe par l'objet retourné.
- **coverage.py et coroutines** : ni `pytrace`, ni `ctrace`, ni `sysmon` ne remontent les lignes après un `await` dans les coroutines SQLAlchemy async/FastAPI (le code s'exécute pourtant, prouvé par les assertions). Mesure plancher ~92 % ; ne pas tordre le code pour faire mentir l'outil (v. `DECISIONS.md`).
- **Le CSRF avant le routage** : le middleware intercepte avant FastAPI ; sans la garde « cookie d'authentification présent », il transformait le 405 d'un `POST /health` en 403. La sécurité a une fenêtre : on ne protège que ce qui porte des credentials.

### Critères de la phase 2c — vérité du terrain
| Critère | État |
|---|---|
| Tests écrits d'abord (RED) puis GREEN | ✅ RED avant toute implémentation (collection errors : `app.core.totp` absents) ; GREEN : **129 passed** |
| pytest vert | ✅ `pytest --cov=app` → 129 passed |
| Couverture ≥ 80 % | ✅ **89,5 % mesurés** (artefact coverage coroutines, v. `DECISIONS.md`) |
| ruff check + format | ✅ exit 0 |
| mypy strict | ✅ 0 erreur sur 53 fichiers |
| TOTP | ✅ RFC 6238 maison validé par les vecteurs officiels de l'appendice B, fenêtre ±1 pas |
| Codes de secours | ✅ 10 codes stockés hachés SHA-256, consommés à l'usage (rejeu → 401) |
| Défi A2F | ✅ login TOTP → `totp_required` + cookie `mirador_2fa` sans session ; défi à usage unique (rejeu → 401, même code) |
| Mot de passe oublié | ✅ réponse invariante (anti-énumération), jeton 30 min haché à usage unique, reset révoque toutes les sessions |
| Migration Alembic `0004` | ✅ aller-retour `head → base` vérifié, tables hors RLS, colonnes `totp_*` ajoutées |
| CSRF A2F | ✅ enable/disable protégés (403 sans jeton) ; verify/forgot/reset libres sans session |
| Rate limit | ✅ `verify-2fa` 5/min, `forgot` 3/15 min, `reset` 5/h — 429 + `Retry-After` |
| pre-commit passe | ✅ `pre-commit run --all-files` → 11 hooks Passed |
| gitleaks ne détecte rien | ✅ passé dans pre-commit |
| CI backend | ⚠️ job écrit, **non exécuté** (aucun remote GitHub) |

### Pièges rencontrés en phase 2c (à ne pas re-piocher)
- **gitleaks bloque le vecteur RFC** : le secret de test base32 du RFC 6238 (`GEZDGNBV…`) a l'entropie d'une clé API → `generic-api-key` le détecte et refuse le commit. Le secret se décode depuis `b"12345678901234567890"` (les octets ASCII réels du RFC) au lieu d'être écrit littéralement.
- **Format `%n` dans `logger.info`** : `"…| %s%n%s"` est interprété par le formatage printf du logging → `ValueError: unsupported format character 'n'`. Écrire `\\n` dans la chaîne de format, ne pas mettre de `%n`.
- **CSRF intercepte l'anonyme aussi** : dès qu'un cookie d'authentification traîne dans le jar, `forgot`/`reset`/`enable` reçoivent 403 au lieu de 422/200. Les tests de flux de récupération doivent partir anonyme (`client.cookies.clear()`) puisque la page de connexion n'a aucun cookie ; sinon c'est la vérification CSRF qui répond en premier.
- **Rejeu du défi A2F en test** : rejouer le cookie `mirador_2fa` avec les cookies de session du premier succès renvoie 403 (CSRF), pas 401. Vider le jar puis reposer le seul cookie de défi pour isoler la consommation du défi.
- **Formatage des messages de test** : les vecteurs RFC utilisent des timestamps exacts (`totp_at(secret, timestamp)`), les tests de flux utilisent l'heure courante (`totp_at(secret)`) — la primitive accepte les deux, pas le test de l'URI otpauth.
- **E-mail de reset dans le log, pas envoyé** : sans SMTP le lien vit dans `LogEmailSender` ; les tests injectent `FakeEmailSender` via `app.state.email_sender` (les routes le lisent sur `request.app.state`).

### Critères de la phase 2d — vérité du terrain
| Critère | État |
|---|---|
| Tests écrits d'abord (RED) puis GREEN | ✅ RED avant toute implémentation (modules absents → erreurs de collection) ; GREEN : **161 passed** |
| pytest vert | ✅ `coverage run -m pytest` → 161 passed (32 nouveaux : 15 invitations, 12 équipe, 5 garde-modules) |
| Couverture ≥ 80 % | ✅ **87 % mesurés** (artefact coverage coroutines, v. `DECISIONS.md`) |
| ruff check + format | ✅ `ruff check .` + `ruff format .` → 0 erreur / 97 fichiers |
| mypy strict | ✅ 0 erreur sur 65 fichiers |
| pre-commit passe | ✅ `pre-commit run --all-files` → 11 hooks Passed |
| gitleaks ne détecte rien | ✅ passé dans pre-commit |
| Invitations | ✅ admin seul, TTL 7 j, rate limit `invite` 10/h, révocation, acceptation (401 jeton invalide, 403 e-mail différent, 409 déjà membre), lien portant l'organisation |
| Permissions par module | ✅ réponse toujours sur les 5 modules, `none` non stocké (absence de ligne), admin = `edit` partout, garde-modules 403 hors `view` |
| Révocation | ✅ `DELETE /members/{id}` + auto-révocation refusée (400) |
| Journal d'audit | ✅ `invitation.created/revoked/accepted`, `membership.permissions.updated` (avant/après), `membership.revoked` ; lecture limitée aux admins (`GET /audit-logs`) |
| RLS réelle | ✅ requêtes SQL brutes sur `invitations`/`audit_logs` sans `set_tenant` → zéro ligne (piège constaté en test) |
| CI backend | ⚠️ job écrit, **non exécuté** (aucun remote GitHub) |

### Pièges rencontrés en phase 2d (à ne pas re-piocher)
- **RLS et SQL brut dans les tests** : toute requête `text(...)` sur une table tenant (`invitations`, `audit_logs`, `memberships`, `module_permissions`) doit d'abord `await set_tenant(session, organization_id=…)`, sinon la RLS ne renvoie aucune ligne et le test échoue sur « introuvable » au lieu de dire pourquoi.
- **CSRF sur `DELETE`** : le middleware n'a pas d'exemption de méthode — une écriture `DELETE` sans `headers=csrf_headers(client)` reçoit 403 avant même le routeur.
- **Le service refuse d'inviter un membre** (409 voulu) : le test « acceptation d'une invitation alors qu'on est déjà membre » ne peut pas passer par l'API pour la 2ᵉ invitation ; il l'insère directement en SQL (jeton haché via `generate_token`/`hash_token`).
- **Disque plein au milieu de la phase** : chaque session de tests laissait un cluster pgserver (~50 Mo) dans `%TEMP%`. Corrigé par `cleanup_mode="delete"` dans `tests/conftest.py` ; vérifier qu'aucun `mirador-pg-*` ne subsiste après un run.

### Critères de la phase 2e — vérité du terrain
| Critère | État |
|---|---|
| Tests écrits d'abord (RED) puis GREEN | ✅ RED avant toute implémentation (erreur de collection : `OAUTH_STATE_COOKIE` absent de `constants.py`) ; GREEN : **179 passed** |
| pytest vert | ✅ `coverage run -m pytest` → 179 passed (18 nouveaux : 13 parcours + 5 fournisseur) |
| Couverture ≥ 80 % | ✅ **88 % mesurés** (`routers/google.py` 87 %, `services/oidc.py` 100 % ; écart restant = artefact coverage coroutines, v. `DECISIONS.md`) |
| ruff check + format | ✅ `ruff check .` + `ruff format .` → 0 erreur / 100 fichiers |
| mypy strict | ✅ 0 erreur sur 67 fichiers |
| pre-commit passe | ✅ `pre-commit run --all-files` → 11 hooks Passed (gitleaks inclus) |
| Démarrage | ✅ 302 vers Google avec `state`, cookie `mirador_oauth_state` httpOnly + `Path=/api/v1/auth`, `redirect_uri` conforme à `Settings.google_redirect_uri` |
| Callback | ✅ session complète (200 + cookies + `/auth/me`), état à usage unique (effacé au succès) ; mismatch d'état, état absent, code absent → 400 sans appel au fournisseur ; `error=…` → 400 « annulée » |
| Garde-fous | ✅ compte absent → 403, e-mail non vérifié → 403, `OidcProviderError` → 502 message figé (détail au journal), fournisseur absent → 404, quota `google` 10/min → 429 |
| A2F conservée | ✅ compte à TOTP actif → `totp_required=true` + cookie `mirador_2fa`, **aucun** cookie de session |
| Fournisseur réel | ✅ tests unitaires `authorization_url` / `exchange_code` via `httpx.MockTransport` (URLs et paramètres Google vérifiés, refus 400 et userinfo sans e-mail → `OidcProviderError`) |
| CI backend | ⚠️ job écrit, **non exécuté** (aucun remote GitHub) |

### Pièges rencontrés en phase 2e (à ne pas re-piocher)
- **Le cookie d'état sur un 302** : il faut le poser sur la `RedirectResponse` retournée, pas sur la `Response` injectée (FastAPI n'en recopie pas les en-têtes quand on retourne une `Response`) — même piège que le 204 de la phase 2b.
- **L'état n'est pas effacé quand le callback échoue** : les 400/403/502 passent par les handlers, qui construisent une réponse neuve sans nos cookies. Sans risque (le cookie ne vaut que pour ce navigateur et expire en 10 min, il est régénéré au démarrage), mais à revoir si le parcours évolue.
- **`OidcProviderError` sans handler = 500** : l'exception vient du fournisseur, pas de FastAPI — elle a besoin de son handler dédié (502 + journal) sinon elle remonte en erreur interne générique.
- **Anomalie coverage visible sur `google.py`** : les lignes après `await` (cookies, retours) sont exécutées et testées mais non mesurées — c'est l'artefact déjà documenté, pas un trou de couverture ; `services/oidc.py` est à 100 %.

### Critères de la phase 3a — vérité du terrain
| Critère | État |
|---|---|
| TypeScript strict | ✅ `npm run typecheck` (`tsc -b`) : 0 erreur ; `strict`, `noUnusedLocals/Parameters`, `verbatimModuleSyntax`, `erasableSyntaxOnly` |
| ESLint | ✅ `eslint .` (flat, JS + TS typé + React Hooks par nom + react-refresh) : 0 erreur |
| Vitest | ✅ `npm test` : 1 test composant (RTL + jest-dom, jsdom), setup de nettoyage DOM |
| Build | ✅ `npm run build` (`tsc -b && vite build`) : 17 modules, 219 kB js / 68 kB gzip (React 19.3.0) |
| Proxy dev | ✅ `/api` → `127.0.0.1:8000` (same-origin, pas de CORS en dev) |
| Épinglage | ✅ toutes versions exactes (sans caret) ; TS `5.9.3` (TS 7 non compatible typescript-eslint) ; `npm install` sans conflit de peers |
| pre-commit | ✅ `pre-commit run` staged : 10 hooks Passed, eslint actif (pass_filenames: false, le hook exact passe les chemins racine qu'on ne peut pas transmettre à npm) |
| CI frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### Pièges rencontrés en phase 3a (à ne pas re-piocher)
- **TS 7 est « latest » mais bloquant** : `typescript-eslint` 8.71.1 déclare un peer `typescript >=4.8.4 <6.1.0` → `npm install` avec TS 7 échouerait ; on reste sur 5.9.3 et on remontera quand le plugin suivra (v. `DECISIONS.md`).
- **`@eslint/js` et `eslint` n'ont pas la même numérotation** : 10.0.1 vs 10.12.0 — vérifier le peer `eslint ^10` au lieu de croire à une égalité de versions.
- **Le bundle de règles React Hooks varie selon la version** : ne pas invoquer `configs.recommended`, épinger `rules-of-hooks` / `exhaustive-deps` par nom (v. `DECISIONS.md`).
- **Vitest jsdom démarre lentement** (~45 s pour 1 test) : c'est le coût de l'environnement DOM, pas de la suite ; ne pas déduire une lenteur de tests de cette première exécution.

### Critères de la phase 3b — vérité du terrain
| Critère | État |
|---|---|
| TypeScript strict | ✅ `npm run typecheck` (`tsc -b`) : 0 erreur |
| ESLint | ✅ `eslint .` : 0 erreur, 0 avertissement |
| Vitest | ✅ `npm test` : **5 fichiers / 10 tests** (App+coquille, KpiCard, ChartCard, EmptyState, ErrorState) |
| Build | ✅ `npm run build` : 2433 modules, 530,74 kB js / 169,22 kB gzip ; **avertissement Vite** « chunk > 500 kB » assumé (v. `DECISIONS.md`) |
| Design tokens | ✅ couleurs + rayons en variables CSS (`:root`/`.dark`), exposés par `@theme inline` |
| Thème clair/sombre | ✅ classe `.dark` (hook `useTheme`) + script d'amorçage dans `index.html` (pas de flash) |
| Layout | ✅ `AppShell` menu latéral gauche, topbar (thème + langue), overlay mobile + fermeture Échap, lien d'évitement, `aria-current` actif |
| Composants de base | ✅ Button, Card, KpiCard (compteur animé), ChartCard, Skeleton, EmptyState, ErrorState |
| i18n FR/EN | ✅ i18next `initAsync:false`, `<html lang>` suivi, aucun texte en dur |
| Routing | ✅ React Router ; pages placeholder à états vides, aucune donnée en dur (AGENTS.md §8) |
| `prefers-reduced-motion` | ✅ transitions de page (Motion) et compteurs neutralisés |
| pre-commit | ✅ `pre-commit run --all-files` : 11 hooks Passed (gitleaks inclus) |
| CI frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### Pièges rencontrés en phase 3b (à ne pas re-piocher)
- **i18next v26 renomme `initImmediate` en `initAsync`** : `initImmediate` n'existe plus dans `InitOptions` → `tsc` échoue. Utiliser `initAsync: false`.
- **`@typescript-eslint/stylistic` impose `interface`** : tout alias d'objet (`export type X = { … }`) est refusé par `consistent-type-definitions` ; garder `type` uniquement pour les unions/utilitaires (`ModuleKey`, `ClassValue`).
- **react-refresh n'admet que des composants** : exporter une fonction utilitaire (`buttonVariants`) depuis un fichier composant déclenche un avertissement ; l'isoler dans `button-variants.ts`.
- **`buttonVariants` pour un `<Link>`** : un `<Link>` ne peut pas envelopper un `<button>` (HTML invalide) ; on réapplique les classes de bouton au lien.
- **Motion + jsdom** : les transitions de page ne bloquent pas les tests (les éléments sont dans le DOM indépendamment de l'opacité), mais les compteurs animés seraient non déterministes → on force `usePrefersReducedMotion` à `true` dans le test de `KpiCard`.
- **Tailwind v4 : pas de `tailwind.config`** : les tokens vivent dans `index.css` via `@theme inline` ; une couleur sémantique absente de ce bloc n'a pas d'utilitaire (`bg-…`).

### Critères de la phase 3c — vérité du terrain
| Critère | État |
|---|---|
| Tests écrits d'abord (RED) puis GREEN | ✓ RED confirmé (imports `client.ts`/`AuthProvider.tsx` introuvables + gardes absentes) ; GREEN : **30 passed** (8 fichiers) |
| Vitest vert | ✓ `npm test` → 30 passed (client CSRF, AuthProvider, gardes, App) |
| Lint | ✓ `npm run lint` (ESLint) : 0 erreur (`schema.d.ts` généré exclu) |
| Types | ✓ `npm run typecheck` (`tsc -b`) : 0 erreur |
| Build | ✓ `npm run build` : 2443 modules, 544 kB js / 173 kB gzip (avertissement chunk > 500 kB assumé) |
| Client API typé | ✓ `openapi-typescript` + `openapi-fetch` ; CSRF double-submit sur écritures ; `ApiError` RFC 9457 ; `unwrap` |
| Schéma OpenAPI | ✓ exporté par `backend/scripts/export_openapi.py` vers `frontend/openapi/schema.json` (commité), types générés |
| Auth front | ✓ `AuthProvider` (loading/anonymous/authenticated/error), org active mémorisée sinon première, `/permissions` chargées |
| Gardes | ✓ `RequireAuth` (redirection `/login`), `RequireModule` (403 si `none`), `RequireAdmin` (403 si non-admin) |
| Menu latéral | ✓ modules filtrés par permission, `Équipe` réservée aux admins ; `analytics` → `web` |
| i18n | ✓ clés `nav.web`, `login.*`, `forbidden.*` (FR + EN), aucun texte en dur |
| pre-commit | ✓ hooks passés (gitleaks inclus) |
| CI frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### Pièges rencontrés en phase 3c (à ne pas re-piocher)
- **`new Request(chemin relatif)` échoue sous Node** : openapi-fetch construit un `Request` ; sans `baseUrl`, une URL relative lève « Failed to parse URL » en test (undici). Solution : `baseUrl: window.location.origin` (same-origin en dev comme en prod).
- **`fetch` capturé à la création du client** : `openapi-fetch` fige `globalThis.fetch` à l'import, donc `vi.stubGlobal('fetch', …)` ne l'atteint pas. Solution : passer `fetch: (input) => globalThis.fetch(input)` pour résoudre au moment de l'appel.
- **Réponse 204 avec corps illégal** : `new Response('{}', { status: 204 })` lève ; pour un logout simulé, utiliser `new Response(null, { status: 204 })`.
- **`U+FFFD` (caractère de remplacement)** : un accent écrit par le mauvais canal devient U+FFFD (`EF BF BD`) et casse les correspondances de texte des tests ; vérifier les points de code des libellés FR.
- **Texte de chargement i18n** : `common.loading` se termine par un point de suspension (…), pas un point ASCII — matcher par regex, pas par chaîne exacte.
- **`schema.d.ts` généré fait échouer ESLint** (règles de style sur les index signatures) : l'ajouter aux `ignores` d'`eslint.config.js`.
- **`consistent-type-definitions`** : `ApiResult<T>` doit être une `interface` (le preset stylistic refuse l'alias d'objet).

### Critères de la phase 3d-c (e2e Playwright + a11y) — vérité du terrain
| Critère | État |
|---|---|
| Playwright e2e : accès à app | ✅ installation `@playwright/test@1.64.0` épinglée, `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` + `channel: 'msedge'` (pas de téléchargement Chromium) |
| e2e parcours connexion | ✅ **3 passed** (`login.spec.ts`) : identifiants valides → dashboard, incorrects → erreur sans navigation, compte A2F → redirection `/2fa` |
| Mocks API fictifs | ✅ `installApiMocks` (helpers.ts) : `me`, `login`, `permissions` interceptés, données fictives (AGENTS.md §5), backend FastAPI volontairement absent |
| Vérification a11y de base | ✅ **axe-core 4.13.0** (`@axe-core/playwright@4.13.0`) : scan `/login` + dashboard authentifié, seuil = zéro violation `serious`/`critical` (WCAG AA), **2 passed** |
| `prefers-reduced-motion` en e2e | ✅ audit exécuté en `reducedMotion: 'reduce'` : neutralise les fondus `PageTransition` (sinon axe mesure le contraste *pendant* l'animation) et vérifie le respect de la réduction |
| Vitest / typecheck / lint / build | ✅ 30 passed · `tsc -b` 0 erreur · `eslint .` 0 erreur · `npm run build` OK |
| pre-commit | ✅ en attente au commit (gitleaks inclus) |
| CI frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### Piège rencontré en phase 3d-c (à ne pas re-piocher)
- **Axe mesure le contraste *pendant* les animations d'entrée** : le `PageTransition` (Motion) fait un fondu ~0,2 s ; scanné en plein vol, axe mélange les couleurs du token avec le fond via l'opacité partielle et signale un faux échec `color-contrast` (ex. `--text` mesuré `#c1c1c3` au lieu de `#16161a`). Les couleurs calculées (`getComputedStyle`) étaient pourtant correctes. Solution : lancer l'audit avec `contextOptions: { reducedMotion: 'reduce' }` (état final stable) — en test comme en phase 11 (audit automatisé).
au premier push GitHub (réglages de dépôt, hors code)
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

### 2026-10-08 — Sous-phase 2b livrée
- TDD respecté : RED (44 failed / 52 passed — zéro erreur de collection) avant toute implémentation, puis GREEN (98 passed).
- Authentification : `/auth/register` (201), `/auth/login` (200), `/auth/refresh` (rotation des jetons), `/auth/logout` (204, révocation), `/auth/me` (200) ; erreurs RFC 9457.
- Sécurité : argon2-cffi (params OWASP), e-mail normalisé + SIREN Luhn, anti-énumération par hachage factice, cookies httpOnly/SameSite=lax/`Secure` en prod, CSRF double submit sur couche middleware (exemptes register/login, exigé seulement si cookies d'auth présents), rate limit en mémoire (429 + Retry-After), en-têtes de sécurité partout (jusqu'aux erreurs).
- Table `sessions` (migration `0003`) : globale sans RLS, SHA-256 des jetons, rotation à chaque refresh, révocation au logout.
- Infrastructure de test : `clean_tables` (TRUNCATE autouse) règle l'isolation des e-mails uniques entre tests qui commitent.
- Vérifications : 98 passed · couverture **92 % mesurés** (artefact coverage sur les coroutines, documenté) · ruff ✅ · format ✅ · mypy strict ✅ (38 fichiers) · pre-commit ✅ · gitleaks ✅ · CI non exécutée sans remote.
- **Non fait** : commit (en attente de ce paragraphe), dernier coup d'œil à `CHANGELOG.md` / `ARCHITECTURE.md` / `PROGRESS.md` au moment du commit.

### 2026-10-08 — Sous-phase 2c livrée
- TDD respecté : RED avant toute implémentation (collection errors sur les modules absents), puis GREEN (**129 passed**).
- A2F TOTP maison (`app/core/totp.py`, RFC 6238 validé par les vecteurs officiels), secret 20 octets base32, fenêtre ±1 pas ; activation en une étape (secret + URI otpauth + 10 codes de secours affichés une fois), réactivation régénère tout, désactivation exige le mot de passe courant.
- Défi de connexion : login TOTP → `LoginResponse(totp_required=true)` + cookie `mirador_2fa` (5 min, confiné à `/api/v1/auth`) + défi `auth_challenges` à usage unique (jeton haché) ; `POST /auth/2fa/verify` échange code TOTP **ou** code de secours contre une session, puis consomme le défi et le code.
- Récupération : `POST /auth/password/forgot` (réponse invariante, anti-énumération, 1 e-mail max par compte) → jeton `password_reset_tokens` 30 min haché à usage unique ; `POST /auth/password/reset` change le mot de passe et révoque toutes les sessions.
- E-mails : interface `EmailSender` + `LogEmailSender` (SMTP à la phase 11), lien de reset construit sur `Settings.app_base_url` ; `AuthChallenges`/`BackupCodes`/`PasswordResetTokens` hors RLS (données d'identité globales), migration `0004`.
- Rate limits dédiés (`verify-2fa` 5/min, `forgot` 3/15 min, `reset` 5/h) ; `.env.example` documente `APP_BASE_URL`.
- Vérifications : 129 passed · couverture 89,5 % · ruff ✅ · format ✅ · mypy strict ✅ (53 fichiers) · pre-commit ✅ (11 hooks, gitleaks inclus) · `.env.example` en phase avec `Settings`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert).

### 2026-10-08 — Sous-phase 2d livrée
- TDD respecté : RED avant toute implémentation (modules absents → erreurs de collection), puis GREEN (**161 passed**, dont 32 nouveaux).
- Invitations : `POST /organizations/{id}/invitations` (admin seul, TTL 7 j, rate limit `invite` 10/h, e-mail via `EmailSender`), révocation `DELETE …/invitations/{id}`, acceptation `POST /auth/invitations/accept` (compte authentifié, e-mail correspondant ; 401 jeton absent/expiré, 403 autre e-mail, 409 déjà membre) — le lien contient le jeton **et** l'organisation, `accept` pose le tenant avant de lire (table sous RLS).
- Équipe : `GET /organizations/{id}/members`, `GET /permissions` (les 5 modules, `none` non stocké, admin = `edit` partout), `PATCH /members/{user_id}/permissions` (audit avant/après), `DELETE /members/{user_id}` (auto-révocation refusée), `GET /audit-logs` (admin) ; garde-modules `require_module` en 403 sur `view`/`edit`.
- Schémas `schemas/invitations.py` + `schemas/team.py`, routers `invitations.py` + `team.py` (câblés dans `main.py`), erreurs levées par les services via `ServiceProblem` (aucun `try/except` dans les routes).
- Journal d'audit : `invitation.created/revoked/accepted`, `membership.permissions.updated`, `membership.revoked`.
- Hygiène : `ruff check` + `ruff format` (9 fichiers reformattés), `mypy` 0 erreur (65 fichiers), `pre-commit run --all-files` → 11 hooks ✅ (gitleaks inclus).
- Fix infra : `tests/conftest.py` → `cleanup_mode="delete"` (les clusters pgserver de test remplissaient `%TEMP%`, ~50 Mo par exécution — disque tombé à 10 Mo en cours de phase).
- Docs : `ARCHITECTURE.md` (bloc invitations/équipe/audit, quotas, nettoyage des clusters), `DECISIONS.md` (6 décisions), `CHANGELOG.md`, `README.md`, ce fichier.
- Commit : `9d7045e feat: invitations, permissions par module et journal d'audit (sous-phase 2d)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert).

### 2026-10-08 — Sous-phase 2e livrée (connexion Google OIDC)
- TDD respecté : RED avant toute implémentation (erreur de collection : `OAUTH_STATE_COOKIE` et `app.services.oidc` absents), puis GREEN (**179 passed**, dont 18 nouveaux).
- Routes : `GET /auth/google` (état opaque en cookie httpOnly 10 min + 302 vers Google) et `GET /auth/google/callback` (comparaison à temps constant, échange du code, session ou défi A2F) ; `app/routers/google.py`, service `app/services/oidc.py` (`OidcProvider` en protocole, `GoogleOidcProvider` réel, `FakeOidcProvider` en test), `authenticate_google` dans `services/auth.py` (jamais de création de compte).
- Garde-fous : compte absent → 403, e-mail non vérifié → 403, fournisseur absent → 404, `OidcProviderError` → 502 (handler dédié, message figé, détail au journal), quota `google` 10/min partagé démarrage/callback ; A2F TOTP toujours exigée (défi `mirador_2fa`, aucun cookie de session).
- Config : `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (vide = routes en 404), `Settings.google_redirect_uri` dérivé de `app_base_url`, `httpx==0.28.1` promu dépendance runtime, `.env.example` mis à jour.
- Qualité : ruff ✅ · format ✅ · mypy strict ✅ (67 fichiers) · pre-commit ✅ (11 hooks, gitleaks inclus) · couverture 88 % (artefact coverage coroutines, v. `DECISIONS.md`).
- Docs : `ARCHITECTURE.md` (bloc Google + quota `google`), `DECISIONS.md` (6 décisions : compte existant uniquement, userinfo sans JWT, cookie d'état, A2F conservée, URI dérivée, 502 dédié), `CHANGELOG.md`, `README.md`, ce fichier.
- Commit : `5a735bc feat: connexion Google OIDC (sous-phase 2e)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; tests manuels avec un vrai compte Google (aucun identifiant réel dans ce dépôt public).

### 2026-10-08 — Phase 3 ouverte, sous-phase 3a livrée (socle frontend)
- Socle `frontend/` : Vite 8.3.4 + React 19.3.0 + TypeScript strict 5.9.3 + ESLint flat + Vitest 5.0.3 (jsdom) ; `tsconfig` décomposés (app + node), `erasableSyntaxOnly`, build par incréments ; toutes les versions épinglées **sans caret**, install sans conflit de peers.
- Proxy de dev `/api` → `127.0.0.1:8000` (same-origin, pas de CORS en dev, v. `DECISIONS.md`) ; `PROJECT_NAME` centralisé dans `src/constants.ts` et posé sur `document.title` ; écran provisoire `App.tsx` + premier test Vitest (RTL + jest-dom).
- Vérifs : `npm run lint` ✅ · `npm run typecheck` ✅ · `npm test` (1 test) ✅ · `npm run build` ✅ (219 kB js / 68 kB gzip) ; hook eslint de pre-commit actif (config corrigée : `pass_filenames: false`, confirmé sur ce commit).
- Commit : `1d675ef feat: socle frontend Vite + React + TypeScript strict (sous-phase 3a)`.
- **Non fait** : push (aucun remote GitHub), merge (sans feu vert) ; design tokens, layout, i18n, client API (sous-phases 3b à 3d).

### 2026-10-09 — Sous-phase 3b livrée (design system & layout)
- TDD adapté : les tests Vitest des composants ont été écrits avec/avant leur implémentation, puis GREEN (**5 fichiers / 10 tests**) ; pas de RED formel (composants neufs, pas de bug à reproduire).
- Design tokens : couleurs + rayons en variables CSS (`:root` clair, `.dark` sombre) exposées à Tailwind v4 par `@theme inline` ; les composants n'utilisent que des tokens sémantiques. Mode sombre piloté par la classe `.dark` (hook `useTheme`, `localStorage`), amorcé par un script inline dans `index.html` pour éviter le flash.
- Layout : `AppShell` (menu latéral gauche, topbar collante thème + langue, overlay mobile avec fermeture Échap, lien d'évitement, `aria-current` actif), `Sidebar`, `Topbar`, `ThemeToggle`, `LanguageSwitcher`, `PageTransition` (Motion, `prefers-reduced-motion` respecté).
- Composants de base : `Button` (+ `button-variants` pour styler un `<Link>`), `Card`, `KpiCard` (compteur animé, tendance), `ChartCard` (états chargement/vide/prêt), `Skeleton`, `EmptyState`, `ErrorState`.
- i18n FR/EN (i18next `initAsync:false`, `<html lang>` suivi, aucun texte en dur) ; routing React Router (`createBrowserRouter`, table `app/routes.tsx`) ; pages placeholder à états vides, sans données en dur (AGENTS.md §8).
- Vérifs : `npm run typecheck` ✅ · `npm run lint` ✅ (0 erreur/avertissement) · `npm test` → 10 passed · `npm run build` ✅ (avertissement « chunk > 500 kB » documenté) · `pre-commit run --all-files` → 11 hooks ✅ (gitleaks inclus).
- Docs : `ARCHITECTURE.md` (structure frontend + design system/layout/i18n), `DECISIONS.md` (6 décisions : Tailwind/tokens, primitives maison vs shadcn/ui, libs, amorçage thème, bundle), `CHANGELOG.md`, `README.md`, ce fichier.
- Commit : `40b9b5a feat: design system, layout avec menu latéral et composants de base (sous-phase 3b)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; client API généré, gardes de routes et vraies pages (3c/3d).

### 2026-10-09 - Sous-phase 3c livrée (client API typé & gardes de routes)
- TDD : RED d'abord (échecs de résolution d'imports + gardes absentes), puis GREEN (**30 tests** sur 8 fichiers).
- Client API typé : `backend/scripts/export_openapi.py` → `frontend/openapi/schema.json` ; `openapi-typescript@7.13.0` génère `src/api/schema.d.ts` (script npm `generate:api`, exclu d'ESLint) ; `openapi-fetch@0.17.0` dans `src/api/client.ts` (baseUrl = origine, credentials include, CSRF double-submit `mirador_csrf` → `x-csrf-token`, `ApiError` RFC 9457, `unwrap`).
- Auth & gardes : `src/auth/context.ts` + `AuthProvider.tsx` (états loading/anonymous/authenticated/error, org active mémorisée sinon première, permissions par org) ; `guards.tsx` (`RequireAuth`/`RequireModule`/`RequireAdmin`, 403 via `ForbiddenPage`) ; pages `LoginPage`, `ForbiddenPage`, `TeamPage` ; `app/routes.tsx` refondu ; `Sidebar` filtrée ; `analytics` → `web` (route, i18n, dashboard).
- Vérifs : `npm test` 30 passed ; `npm run lint` 0 erreur ; `npm run typecheck` 0 erreur ; `npm run build` OK (avertissement chunk assumé) ; pre-commit (gitleaks inclus).
- Docs : `ARCHITECTURE.md`, `DECISIONS.md` (7 décisions), `CHANGELOG.md`, `README.md`, ce fichier.
- Commit : `0c70367 feat: client API typé et gardes de routes (sous-phase 3c)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; pages réelles connexion/inscription/A2F/équipe et e2e Playwright (3d).


### 2026-10-09 — Refonte visuelle du frontend (ajustement hors feuille de route)
- Demande en cours de phase 3 : « pimper » le dashboard. Direction validée après revue de galeries d'inspiration (kombai, 5sdesign) : clair aéré type Linear/Notion + rail d'icônes rétractable + topbar riche + tableau de bord bento asymétrique.
- Tokens (`index.css`) : palette claire (`--background #f7f7f8`, `--surface #fff`, `--border`, `--brand #5b5bd6`, `--brand-glow`), variante sombre, rayons `--radius-sm…xl`, élévations `--elevation-1/2` → `--shadow-card`/`--shadow-raised`, halo `radial-gradient` discret sur `body` (fixé), mapping `@theme inline`.
- Shell : rail rétractable (`Sidebar`, `SidebarNavItem` avec prop `collapsed`, largeur `--rail-w` 16rem/4.75rem, état persisté `mirador-rail-collapsed` via `useRailCollapsed`, libellés masqués + `title`), `Topbar` (fil d'ariane par route, identité + rôle, langue, thème), `AppShell` (`lg:pl-[var(--rail-w)]`, skip-link).
- Dashboard : grille 12 colonnes asymétrique (WelcomePanel 8 = accès rapide réel vers modules autorisés, ActivityPanel 4 = état vide) + 4 `ChartCard` 7/5 puis 5/7 ; aucune donnée en dur (AGENTS.md §8).
- Pages : nouvelle primitive `PageHeader` ; `ModulePage`, `TeamPage`, `ForbiddenPage` migrées ; `Card` passe à `border-border bg-surface shadow-card` ; helper `src/lib/permissions.ts` (`canSeeModule`).
- Tests : liens en double (rail + accès rapide) corrigés, `App.test.tsx` et `auth/guards.test.tsx` réécrits (`within(nav)`, `findAllByText`) ; **30 passed** (8 fichiers).
- Vérifs : `npm run typecheck` ✅ · `npm run lint` ✅ · `npm test` 30 passed · `npm run build` ✅ · 0 U+FFFD dans `frontend/src`.
- Docs : `DECISIONS.md` (2026-10-09), `CHANGELOG.md`, ce fichier.
- **Non fait** : commit (à faire), push (aucun remote GitHub), merge sur `main` (sans feu vert).


### 2026-10-09 — Sous-phase 3d-a livrée (TanStack Query + inscription + mot de passe oublié)
- TanStack Query 5.104.1 installé ; QueryClientProvider dans `main.tsx` (retry false, refetchOnWindowFocus false) ; `AuthProvider` migré de useState/useEffect vers `useQuery` (queries `authKeys.me` et `authKeys.permissions`, invalidation pour reload).
- Pages `RegisterPage` (POST /auth/register → org + admin), `ForgotPasswordPage` (POST /auth/password/forgot, réponse anti-énumération), `ResetPasswordPage` (POST /auth/password/reset, token en query param) ; routes `/register`, `/forgot-password`, `/reset-password` ajoutées.
- `LoginPage` migré vers `useMutation` ; liens vers inscription et mot de passe oublié ajoutés.
- i18n : clés `register.*`, `forgotPassword.*`, `resetPassword.*`, `login.forgotPassword`, `login.noAccount` (FR + EN).
- Tests : `AuthProvider.test.tsx`, `guards.test.tsx`, `App.test.tsx` mis à jour avec QueryClientProvider ; **30 passed** (8 fichiers).
- Vérifs : `npm run typecheck` ✅ · `npm run lint` ✅ · `npm test` 30 passed · `npm run build` ✅ (bundle 600 kB js / 188 kB gzip — TanStack Query inclus).
- **Non fait** : commit (à faire), push (aucun remote GitHub), merge sur `main` (sans feu vert).


### 2026-10-09 — Sous-phase 3d-b livrée (A2F complet)
- Page `TwoFactorPage` (`/2fa`) : défi 2FA après `totp_required` au login → `POST /auth/2fa/verify` (code TOTP ou code de secours).
- Page `SettingsPage` (`/settings`) : activation TOTP (`POST /auth/2fa/enable` → secret, otpauth_url, backup_codes), désactivation (`POST /auth/2fa/disable`).
- `LoginPage` : redirection vers `/2fa` au lieu du message `totpUnsupported` ; `totp_required` géré via `useMutation`.
- Routes `/2fa` (publique) et `/settings` (protégée) ajoutées ; lien Paramètres dans la sidebar.
- i18n : clés `twoFactor.*`, `settings.*`, `nav.settings` (FR + EN).
- Tests : **30 passed** (8 fichiers) — pas de nouveaux tests pour 2FA (pas de backend disponible pour les tests d'intégration).
- Vérifs : `npm run typecheck` ✅ · `npm run lint` ✅ · `npm test` 30 passed · `npm run build` ✅ (bundle 608 kB js / 189 kB gzip).
- Commit : `4fc2422 feat: pages A2F et paramètres (sous-phase 3d-b)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert).

### 2026-10-10 — Sous-phase 3d-c livrée (e2e Playwright du login + vérification a11y de base)
- Playwright : `@playwright/test@1.64.0` épinglé, installé avec `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`, navigateur = Edge installé (`channel: 'msedge'`, pas de Chromium téléchargé). `playwright.config.ts` : `testDir ./e2e`, `webServer` Vite dev (reuseExistingServer), baseURL `http://localhost:5173`.
- Mocks (AGENTS.md §5, données fictives) : `e2e/helpers.ts` intercepte `/api/v1/auth/me`, `/api/v1/auth/login`, `/api/v1/organizations/*/permissions` (org et user fictifs `1111…/2222…`) ; état pilotable par les tests (connecté / défi A2F / rejet du login) ; le backend FastAPI ne tourne pas.
- `e2e/login.spec.ts` : 3 tests passent — identifiants valides → dashboard (nom de l'org affiché), mauvais identifiants → `Alert` d'erreur sans navigation (reste sur `/login`), compte A2F → redirection `/2fa`.
- A11y : `@axe-core/playwright@4.13.0` ; `e2e/a11y.spec.ts` scanne `/login` et le dashboard authentifié avec le seuil « zéro violation serious/critical » (WCAG AA) ; les 2 tests passent.
- **Piège résolu** : axe levait un faux `color-contrast` sur le dashboard — le scan tombait pendant le fondu d'apparition du `PageTransition` (opacité ~0,3) et mélangeait les couleurs. Fix : `test.use({ contextOptions: { reducedMotion: 'reduce' } })` → animation neutralisée (état final stable) et réduction des animations vérifiée au passage (SPEC §7).
- Config : script `test:e2e` (package.json), Vitest exclut `e2e/**` (vite.config.ts), override ESLint `globals: node` pour `e2e/**` + `playwright.config.ts`, `tsconfig.node.json` inclut `playwright.config.ts` + `e2e` (`allowImportingTsExtensions`).
- Vérifs : `npm run typecheck` ✅ · `npm run lint` ✅ · `npm test` 30 passed · `npm run build` ✅ · `npx playwright test` 5 passed.
- Docs : CHANGELOG, ce fichier.
- **Non fait** : commit 3d-c (à faire), push (aucun remote GitHub), merge sur `main` (sans feu vert) ; phase 4 à venir.

### 2026-10-10 — Phase 3 clôturée et mergée sur `main`
- Commit de la sous-phase 3d-c : `21f3a69` (11 fichiers, +307/−6 ; nouveaux `frontend/e2e/a11y.spec.ts`, `helpers.ts`, `login.spec.ts`, `frontend/playwright.config.ts`). Vérifs de fin de phase : Vitest 30/30, typecheck/lint 0 erreur, build OK, `npx playwright test` 5/5, pre-commit 11 hooks OK (gitleaks inclus).
- Correction en route : `"moduleDetection": "force"` restauré dans `frontend/tsconfig.node.json` (suppression accidentelle antérieure, confirmée via `git show HEAD:...`).
- La branche `main` n'existait pas : créée à la pointe `21f3a69` (`git branch main HEAD`), puis checkout — toutes les phases 0→3 sont des ancêtres linéaires.
- **Branche actuelle** : `main` (pointe sur `21f3a69`), attente du feu vert pour ouvrir la phase 4.

### 2026-10-10 — Sous-phase 4a livrée (métriques canoniques, interface Connector, mocks déterministes)
- `app/schemas/metrics.py` : métriques canoniques (SPEC §5.4) — `MetricPoint`, `MetricSeries` (clé `module.metric` validée : module connu, un seul séparateur), `build_metric_key`, `metric_prefix`, constante `PERIOD_DAY` (`P1D`).
- `app/connectors/base.py` : interface `Connector` (provider, category, auth_type, `connect`, `sync(since)`, `handle_webhook`, `disconnect`, `healthcheck`) + `ConnectorHealth`. Les mocks partagent le seed via l'`__init__` de base.
- `app/connectors/mock.py` : `MockConnector` déterministe par seed — valeur d'un jour dérivée uniquement de (seed, clé, date) via SHA-256, sans état mutable. Une métrique réaliste par module : `finance.revenue` (EUR, effet week-end 0,55, bruit, anomalies 3 %), `web.visits`, `projects.tasks_done`, et `social.followers` **cumulé** (croissance hebdomadaire stable depuis 2020, indépendante de la fenêtre demandée). Tendance linéaire + saisonnalité annuelle + anomalies (`_daily_value`, `_cumulative_value`, `build_series`).
- `app/connectors/registry.py` + `__init__.py` : registre par provider, auto-enregistrement des 4 mocks (`mock.finance`, `mock.web`, `mock.social`, `mock.projects`), `make(provider, seed)`, `list_categories()` (ordre trié), `list_connectors(category)`.
- Tests (`tests/connectors/`) : 31 tests — déterminisme du seed (même seed → séries identiques, seed différent → valeurs différentes), réalisme (week-end < semaine pour le CA, anomalie > 1,5 × médiane, tendance dominante sur 2 ans pleins pour annuler la saisonnalité), format canonique, cumul stable, bornes de l'époque, webhook vide, registre.
- Vérifs : pytest 31 passed · ruff ✅ · mypy ✅ (artefact coverage coroutines toujours en vigueur, couverture non mesurée sur ce sous-ensemble).
- **Non fait** : commit (à faire), push (aucun remote GitHub), merge (sans feu vert) ; 4c/4d.

### 2026-10-10 — Sous-phase 4b livrée (table `metric_snapshots`, RLS, service de synchro)
- `app/models/metric_snapshot.py` : table tenant `metric_snapshots` (SPEC §5.3) — `organization_id`, `metric_key` CHECK `^(finance|legal|projects|social|web)\.[a-z0-9_]+$`, `period` CHECK `^P[0-9]+(D|W|M|Y)$`, `value` (double), `dimensions` JSONB, `captured_at` (indexé), `created_at`.
- Migration `0005_phase4_metric_snapshots_and_rls.py` : table + index + unicité `(organization_id, metric_key, captured_at)` + **RLS activée et forcée** avec la politique unique par organisation (même convention que `0002`). `tests/test_alembic.py` mis à jour (`HEAD_REVISION = 0005`, `metric_snapshots` ajoutée aux tables tenant vérifiées — RLS + aller-retour head→base).
- `app/schemas/metrics.py` : `validate_metric_key` extrait (réutilisé par `MetricSeries` et le nouveau `MetricSnapshotIn`).
- `app/repositories/metric_snapshots.py` : `upsert_many` (INSERT … ON CONFLICT DO UPDATE sur l'unicité — re-synchro sans doublon) et `get_series` (fenêtre + limite, tri chronologique, filtre explicite par organisation **et** RLS).
- `app/services/sync.py` : `sync_organization(session, organization_id)` — instancie toutes les démos du registre avec un seed déterministe (`seed_for_organization` = 32 bits faibles de l'UUID), synchronise le lookback (`SYNC_LOOKBACK_DAYS = 365`) et upsert tout en base. Le tenant doit être posé (c'est la RLS qui autorise l'écriture).
- Tests intégration (`tests/connectors/test_metric_snapshots.py`, 5 tests) : les 4 modules écrits, re-synchro idempotente (même comptage), seed stable, isolation entre deux organisations, lecture filtrée par tenant et par fenêtre.
- Vérifs : suite backend complète **216 passed** · ruff ✅ · format ✅ · mypy strict ✅ · pre-commit ✅ (gitleaks inclus).
- **Non fait** : push (aucun remote GitHub), merge (sans feu vert).

### 2026-10-10 — Sous-phase 4c livrée (worker de synchro + `JobScheduler`)
- `app/workers/scheduler.py` : classe `JobScheduler` — boucle asyncio légère, `start`/`stop` idempotents, intervalle en secondes strictement positif, échec du travail journalisé (la boucle continue), propriété `running`.
- `app/workers/sync.py` : `sync_all_organizations(session_factory)` — liste les organisations (nouveau `list_organization_ids` dans le repository), puis pour chacune : session dédiée, tenant posé (`set_tenant`), `sync_organization`, commit ; un échec par organisation est journalisé sans arrêter le passage.
- `app/main.py` : le lifespan démarre le planificateur si `sync_interval_minutes > 0` et le stoppe proprement à l'arrêt. Nouveau paramètre `SYNC_INTERVAL_MINUTES` (défaut 5 min, configurable), documenté dans `.env.example`. Les tests httpx ne déclenchent pas le lifespan : aucun planificateur dans la CI.
- Tests (9) : `test_scheduler.py` (périodicité, idempotence de `start`/`stop`, échec absorbé, intervalle nul/négatif refusé) et `test_sync_worker.py` (toutes les organisations synchronisées, idempotence, panne d'une organisation n'arrête pas les autres, aucune organisation → rien).
- Vérifs : suite backend complète **225 passed** · ruff ✅ · format ✅ · mypy strict ✅ · pre-commit ✅ (gitleaks inclus).
- **Non fait** : commit (à faire), push (aucun remote GitHub), merge (sans feu vert) ; 4d.

### 2026-10-10 — Sous-phase 4d livrée (endpoint de lecture des métriques)
- Migration `0006_phase4_metric_units.py` : ajout de la colonne `unit` à `metric_snapshots` (format canonique, SPEC §5.4) — l'endpoint est générique : il ne connaît pas le connecteur, l'unité est stockée par point. `tests/test_alembic.py` : `HEAD_REVISION = 0006`. Base de dev mise à jour (`alembic upgrade head` → `0006`).
- `app/services/metrics.py` : `get_metric_series` — fenêtre `start`/`end`, `limit`, tri chronologique, série repliée en `MetricSeries` (clé, unité, période, points + dimensions) ; 422 si des bornes inversées, 404 si aucune donnée (`ServiceProblem`).
- `app/routers/metrics.py` : `GET /api/v1/organizations/{organization_id}/metrics/{metric_key}` — garde `view` du module dérivé de la clé canonique (`require_metric_module`), clé invalide → 422. `app/core/permissions.py` : `ensure_module_access` extrait (partagé avec `require_module`).
- `app/models/metric_snapshot.py` + `MetricSnapshotIn` + repository + `sync_organization` : l'unité suit le point jusqu'en base.
- Tests endpoint (9) : lecture admin, fenêtre de dates, limite, membre sans droit → 403, membre avec vue → 200 (et autre module → 403), autre organisation → 403, clé invalide → 422, bornes inversées → 422, série vide → 404.
- Vérifs : suite backend complète **234 passed** · ruff ✅ · format ✅ · mypy strict ✅ (80 fichiers) · pre-commit ✅ (gitleaks inclus).
- **Non fait** : commit 4d (à faire), clôture phase (docs, commit final), push, merge (sans feu vert).

### 2026-10-10 — Clôture de la phase 4 (connecteurs & données fictives)
- Critères AGENTS.md §3 remplis : suite backend **234 tests verts**, ruff + ruff format + mypy strict OK, pre-commit 11 hooks OK (dont gitleaks — aucun secret), docs à jour (README, ARCHITECTURE, DECISIONS, PROGRESS, CHANGELOG).
- Décisions notées dans `docs/DECISIONS.md` (seed par UUID, re-synchro idempotente 365 j, unité par point, planificateur in-process désactivé en test).
- Base de dev à jour (`alembic upgrade head` → `0006`), worker actif toutes les 5 min par défaut au prochain démarrage de l'API.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (en attente d'un feu vert).

### 2026-10-10 — Sous-phase 5a livrée (module Finance — backend + frontend)
Backend :
- `app/connectors/mock.py` refondu : les 3 mocks génériques restants (web/projects/social) ; helpers publics `hash01`/`daily_value`/`cumulative_value` ; `metric_configs()` (tuples de `MockMetricConfig`, nouveau champ `anomalies: bool`).
- `app/connectors/finance.py` : nouveau `MockFinanceConnector` (provider `mock.finance`) riche — 8 séries cohérentes entre elles : revenue/expenses (CA et dépenses quotidiennes EUR, effet week-end + anomalies), margin (= CA − dépenses, peut être négatif un mauvais week-end), cash (cumulée depuis `CREATION_EPOCH`, indépendante de la fenêtre demandée), budget (hebdomadaire lisse, `anomalies=False`), invoices_outstanding (avec `dimensions.aging = [{days, count}]`), top_clients (parts normalisées, somme = 55 % du CA, 5 noms fictifs) et top_suppliers (40 % des dépenses, 4 noms). `sync` surchargé pour la série cumulée (lookback fixe 365 j → dérive limitée).
- Registre : `ALL_CONNECTORS = (MockFinanceConnector, *MOCK_CONNECTORS)` (ordre stable), le connecteur finance enregistre les 8 clés.
- Tests : `tests/connectors/test_finance_mock.py` (11) — cohérence marge, dérivée de la trésorerie (cash[j+1]−cash[j] == net[j+1]), ancienneté décroissante 0-30 > 31-60 > 61+, top clients ≥ 50 % du CA total, déterminisme, registre, séries dans `test_mock_connector.py`/`test_registry.py`/`test_metric_snapshots.py` adaptés (clé finance → job finance).
- **Piège résolu** : la suite complète restait bloquée 10+ min par des processus PostgreSQL orphelins (clusters `%TEMP%\mirador-pg-*` d'un pgserver précédent encore vivants) — 7 processus tués + 2 répertoires purge → **245 passed en 320 s**. ruff ✅ · format ✅ · mypy strict ✅ · pre-commit ✅.
Frontend (page `/finance`, remplace le placeholder) :
- `recharts@3.10.1` installé (épinglé, 36 paquets, 0 vulnérabilité) — justifié dans `docs/DECISIONS.md`.
- `src/metrics/queries.ts` (clés de requête, `fetchMetricSeries`, `POLLING_INTERVAL_MS` 5 min, limite 60) ; `src/metrics/finance.ts` (les 8 clés canoniques, `fetchFinancePanel` en `Promise.all`, séries absentes = 404 → « pas encore connecté », erreurs réelles propagées) ; `src/metrics/format.ts` (Intl : devise, devise compacte, dates, tendance du dernier point).
- `src/components/metrics/MultiSeriesChart.tsx` (un seul enveloppe Recharts, variantes area/bar/line, couleurs par tokens CSS `--brand/--danger/--warning/--success`, libellés i18n fournis par l'appelant) et `RankedList.tsx` (classement avec part proportionnelle).
- `src/pages/FinancePage.tsx` : 4 KPI (CA, trésorerie, marge, impayés) + grille asymétrique (CA vs dépenses 8, ancienneté 4, budget vs réalisé 6, marge 6, top clients/fournisseurs 6+6) ; états chargement/index vide (404 complet)/erreur (+ réessai)/prêt ; note « Données de démonstration fictives » (dépôt public). Route `/finance` branchée ; i18n `finance.*` FR/EN.
- Tests : `FinancePage.test.tsx` (3 — panneau complet, module non connecté, panne réseau), `guards.test.tsx` adapté (la route finance affiche maintenant la vraie page), doublons de texte (KPI « Marge » = titre de graphique) gérés via `getAllByText`.
- Vérifs : Vitest **33 passed** · `npm run lint` ✅ · `npm run typecheck` ✅ · `npm run build` ✅ (avertissement chunk > 500 kB pré-existant) · `npx playwright test` rejoué **5/5** (login + a11y inchangés).
- Docs : `ARCHITECTURE.md` (structure frontend + point 5a), `DECISIONS.md` (7 décisions : Recharts, 8 clés du panneau, 404 = non connecté, parts tops, marge négative, lookback cumul, formatage Intl), `CHANGELOG.md`, ce fichier.
- Commit : `92f2b11 feat: module Finance (page, KPI et connecteur de démo) (sous-phase 5a)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; 5b Web analytics.

### Critères de la phase 5a — vérité du terrain
| Critère | État |
|---|---|
| Tests backend | ✅ suite complète **245 passed** |
| Tests frontend | ✅ Vitest **33 passed** (9 fichiers) |
| Lint/types backend | ✅ ruff check + format ✅ · mypy strict ✅ (81 fichiers) |
| Lint/types frontend | ✅ `npm run lint` 0 erreur · `npm run typecheck` 0 erreur |
| Build | ✅ `npm run build` OK (avertissement chunk > 500 kB pré-existant) |
| Backend Finance | ✅ `MockFinanceConnector` : 8 séries cohérentes (marge = CA − dépenses, trésorerie dérivée, ancienneté, tops) |
| Frontend Finance | ✅ 4 KPI + grille asymétrique, états chargement/vide/erreur, note « données fictives » |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI backend/frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-11 — Sous-phase 5b livrée (module Web analytics — backend + frontend)
Backend :
- `app/connectors/web.py` : nouveau `MockWebConnector` (provider `mock.web`, `category = Module.WEB`) — 10 séries web cohérentes pilotées par les sessions : `web.sessions` (saisonnalité + week-end + bruit), `web.visitors` (fraction des sessions), `web.pageviews` (sessions × pages/session ≥ sessions), `web.engagement_rate` (%), `web.avg_session_duration` (s), `web.conversions`, et quatre répartitions (`web.traffic_sources` = sessions, `web.top_pages` = 60 % des pages vues sur 5 pages, `web.devices` = visiteurs, `web.countries` = visiteurs) au format `dimensions.items = [{name, value}]` sommant exactement la métrique parente. Chemins de pages fictifs ; sources/appareils = clés canoniques traduites côté UI ; pays = codes ISO nommés par `Intl.DisplayNames`.
- `app/connectors/mock.py` : `web.visits` retiré ; `MOCK_CONNECTORS = (MockSocialConnector, MockProjectsConnector)`. `app/connectors/__init__.py` : `ALL_CONNECTORS = (MockFinanceConnector, MockWebConnector, *MOCK_CONNECTORS)`.
- Registre : le connecteur web enregistre les 10 clés (remplace l'ancienne `web.visits`).
- **Piège résolu** : `upsert_many` dépassait la limite asyncpg de 32 767 paramètres par requête (20 séries × 365 jours × 7 colonnes) → découpage en lots (`_MAX_ROWS_PER_STATEMENT = 2 000`), test de non-régression ajouté.
- Tests : `tests/connectors/test_web_mock.py` (12 — 10 séries, cohérences visitors ≤ sessions ≤ pageviews, conversions ≤ sessions, somme exacte des répartitions, week-end, déterminisme du seed, futur vide, registre) ; `test_metric_snapshots.py` (`EXPECTED_KEYS` → 10 clés web).
- Vérifs : connecteurs + registry + snapshots **34 passed** · ruff check + format ✅ · mypy strict ✅ (82 fichiers).
Frontend (page `/web`, remplace le placeholder) :
- `src/metrics/web.ts` : les 10 clés canoniques, `fetchWebPanel` en `Promise.all` (404 → « pas encore connecté », erreurs réelles propagées), `useWebPanel` (polling 5 min).
- `src/metrics/queries.ts` : `isNotFound` déplacé ici (partagé finance/web) et `metricsKeys.panel` étendu à `'finance' | 'web'` ; `finance.ts` importe depuis `queries.ts`.
- `src/metrics/format.ts` : ajout de `formatInteger`, `formatPercent` (ratio 0→1), `formatDuration` (unités `minute`/`second` via `Intl`, sans texte en dur) et `formatCountry` (`Intl.DisplayNames`).
- `src/pages/WebPage.tsx` : 4 KPI (visiteurs, sessions, pages vues, taux de conversion) + grille 9 widgets (sessions vs visiteurs, sources, pages vues, top pages, durée, appareils, pays, engagement) ; états chargement/vide (404 complet)/erreur (+ réessai)/prêt ; note « Données de démonstration fictives ». Route `/web` branchée sur `RequireModule`.
- `src/api/types.ts` : union `WebMetricKey` (10 clés) ; i18n `web.*` FR/EN (libellés sources/appareils + note fictive).
- Tests : `WebPage.test.tsx` (3 — panneau complet, module non connecté, panne réseau, calqués sur `FinancePage.test.tsx`).
- Vérifs : Vitest **36 passed** (10 fichiers) · `npm run lint` ✅ · `npm run typecheck` ✅ · `npm run build` ✅.
- Docs : `DECISIONS.md` (décisions 5b), `CHANGELOG.md`, `README.md`, `ARCHITECTURE.md`, ce fichier.
- Commit : `f3c75af feat: module Web analytics (page, KPI et connecteur de demo) (sous-phase 5b)` (21 fichiers, +1258/−58).
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; sous-phases social/projects/legal.

### Critères de la phase 5b — vérité du terrain
| Critère | État |
|---|---|
| Tests backend | ✅ suite complète **256 passed** (un lancement concurrent avec Vitest a fait échouer le test *flaky* `test_scheduler` par timing, vert en exécution isolée — sans lien avec la 5b) |
| Tests frontend | ✅ Vitest **36 passed** (10 fichiers) |
| Lint/types backend | ✅ ruff check + format ✅ · mypy strict ✅ (82 fichiers) |
| Lint/types frontend | ✅ `npm run lint` 0 erreur · `npm run typecheck` 0 erreur |
| Build | ✅ `npm run build` OK (avertissement chunk > 500 kB pré-existant) |
| Bug corrigé | ✅ limite asyncpg 32 767 paramètres (`upsert_many` par lots) + test de non-régression |
| Backend Web | ✅ `MockWebConnector` : 10 séries cohérentes, répartitions sommant la métrique parente |
| Frontend Web | ✅ 4 KPI + 9 widgets, états chargement/vide/erreur, note « données fictives », libellés i18n |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI backend/frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-11 — Sous-phase 5c livrée (module Réseaux sociaux — backend + frontend)
Backend :
- `app/connectors/social.py` : nouveau `MockSocialConnector` (provider `mock.social`, `category = Module.SOCIAL`) — 9 séries cohérentes pilotées par les abonnés cumulés : `social.followers` (total cumulé depuis `CREATION_EPOCH`, `dimensions.items` = abonnés par réseau LinkedIn/Instagram/Facebook/X/YouTube sommant le total), `social.followers_growth` (variation quotidienne du total, ≥ 0), `social.impressions`, `social.reach` (≤ impressions), `social.engagements` (≤ impressions), `social.engagement_rate` (= interactions/impressions × 100, 2 décimales), `social.mentions`, `social.posts` (nb de publications/jour, week-end plus calme) et `social.top_posts` (`dimensions.items` = 4 meilleurs posts fictifs, interactions, sommant 45 % des interactions). Helpers `followers_by_network`/`posts_for_day`/`ranked_names`/`_followers_point`/`_distribution_point`/`_days`, `TOP_POSTS_COUNT = 4`, `TOP_POSTS_SHARE = 0.45`, 12 titres de posts fictifs.
- `app/connectors/mock.py` : `social.followers` retiré (le module social a désormais son panneau comme finance/web) ; `MOCK_CONNECTORS = (MockProjectsConnector,)`. `app/connectors/__init__.py` : `MockSocialConnector` importé depuis `social`, `ALL_CONNECTORS = (MockFinanceConnector, MockWebConnector, MockSocialConnector, *MOCK_CONNECTORS)`.
- Tests : `tests/connectors/test_social_mock.py` (13 — les 9 séries + tz UTC, abonnés par réseau sommant le total, abonnés cumulés croissants, croissance = variation des abonnés, portée ≤ impressions, interactions ≤ impressions, taux = interactions/impressions, top_posts = 4 items sommant 45 % des interactions, mentions ≥ 0, week-end plus calme, déterminisme du seed, suite vide, registre) ; `test_metric_snapshots.py` (`EXPECTED_KEYS` → 9 clés social).
- Vérifs : connecteurs **89 passed** · ruff check + format ✅ · mypy strict ✅ (83 fichiers) · suite backend complète **268 passed**.
Frontend (page `/social`, remplace le placeholder) :
- `src/metrics/social.ts` : les 9 clés canoniques, `fetchSocialPanel` en `Promise.all` (404 → « pas encore connecté », erreurs réelles propagées), `useSocialPanel` (polling 5 min).
- `src/metrics/queries.ts` : `metricsKeys.panel` étendu à `'finance' | 'web' | 'social'` ; `src/api/types.ts` : union `SocialMetricKey` (9 clés).
- `src/pages/SocialPage.tsx` : 4 KPI (abonnés, impressions, portée, taux d'engagement) + grille de 8 widgets (impressions vs portée, abonnés par réseau, croissance, taux d'engagement, mentions, meilleurs posts, interactions, publications) ; états chargement/vide (404 complet)/erreur (+ réessai)/prêt ; note « Données de démonstration fictives ». Route `/social` branchée sur `RequireModule`.
- i18n `social.*` FR/EN (`social.network.*` pour les 5 réseaux) ; `src/pages/SocialPage.test.tsx` (3 — panneau complet, module non connecté, panne réseau).
- Vérifs : Vitest **39 passed** (11 fichiers) · `npm run lint` ✅ · `npm run typecheck` ✅ · `npm run build` ✅ (avertissement chunk > 500 kB pré-existant).
- Docs : `DECISIONS.md` (décisions 5c), `CHANGELOG.md`, `README.md`, `ARCHITECTURE.md`, ce fichier.
- Commit : `3b27329 feat: module Réseaux sociaux (page, KPI et connecteur de demo) (sous-phase 5c)` (13 fichiers, +1156/−29) ; docs `442c6af`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; sous-phases projects/legal.

### Critères de la phase 5c — vérité du terrain
| Critère | État |
|---|---|
| Tests backend | ✅ suite complète **268 passed** (+12 vs 5b) |
| Tests frontend | ✅ Vitest **39 passed** (11 fichiers) |
| Lint/types backend | ✅ ruff check + format ✅ · mypy strict ✅ (83 fichiers) |
| Lint/types frontend | ✅ `npm run lint` 0 erreur · `npm run typecheck` 0 erreur |
| Build | ✅ `npm run build` OK (avertissement chunk > 500 kB pré-existant) |
| Backend Social | ✅ `MockSocialConnector` : 9 séries cohérentes, abonnés par réseau et top posts sommant leur métrique parente, croissance = variation |
| Frontend Social | ✅ 4 KPI + 8 widgets, états chargement/vide/erreur, note « données fictives », libellés i18n |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI backend/frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-11 — Sous-phase 5d livrée (module Projets & tâches — backend + frontend)
Backend :
- `app/connectors/projects.py` : nouveau `MockProjectsConnector` (provider `mock.projects`, `category = Module.PROJECTS`) — 10 séries cohérentes pilotées par le stock de tâches ouvertes : `projects.tasks_created`/`projects.tasks_done` (rythme quotidien, week-end plus calme), `projects.open_tasks` (stock = différence cumulée créées − terminées depuis `CREATION_EPOCH`, jamais négatif), `projects.overdue_tasks` (≤ stock ouvert), `projects.avg_completion_time` (jours, 1 décimale), `projects.avg_progress` (0-100 %), `projects.active_projects`, et trois répartitions (`projects.tasks_by_status` = stock sur 4 statuts canoniques, `projects.person_load` = stock sur 6 personnes fictives, `projects.upcoming_milestones` = délai restant de 6 jalons génériques) au format `dimensions.items = [{name, value}]` sommant exactement la métrique parente. Helpers `_milestones_point`/`_days_until`/`_distribution_point`/`_days`, `STATUSES`/`PERSONS`/`MILESTONES`, `INITIAL_BACKLOG = 40` (aucun salarié ni client réel, AGENTS.md §5).
- `app/connectors/mock.py` : `projects.tasks_done` et `MockProjectsConnector` retirés (le module projets a désormais son panneau comme les autres) ; `MOCK_METRICS`/`metric_configs()`/`MOCK_CONNECTORS` supprimés, `MockConnector.sync` de base lève `NotImplementedError`. `app/connectors/__init__.py` : `MockProjectsConnector` importé depuis `projects`, `ALL_CONNECTORS = (MockFinanceConnector, MockWebConnector, MockSocialConnector, MockProjectsConnector)`.
- Tests : `tests/connectors/test_projects_mock.py` (12 — les 10 séries + tz UTC, créées en moyenne > terminées, stock ouvert = différence cumulée au quotidien, retards ≤ stock, avancement dans 0-100, délai de livraison raisonnable, projets actifs ≥ 1, statuts/personnes sommant le stock, jalons à venir triés et sommant leur total, déterminisme du seed, suite vide, registre) ; `test_metric_snapshots.py` (`EXPECTED_KEYS` → 10 clés projets).
- Vérifs : ruff check + format ✅ · mypy strict ✅ (84 fichiers) · suite backend complète **280 passed** (+12 vs 5c).
Frontend (page `/projects`, remplace le placeholder) :
- `src/metrics/projects.ts` : les 10 clés canoniques, `fetchProjectsPanel` en `Promise.all` (404 → « pas encore connecté », erreurs réelles propagées), `useProjectsPanel` (polling 5 min).
- `src/metrics/queries.ts` : `metricsKeys.panel` étendu à `'finance' | 'web' | 'social' | 'projects'` ; `src/api/types.ts` : union `ProjectMetricKey` (10 clés) ; `src/metrics/format.ts` : ajout de `formatDays` (unité `day` via `Intl`, sans texte en dur).
- `src/pages/ProjectsPage.tsx` : 4 KPI (tâches terminées, tâches ouvertes, avancement moyen, délai moyen de livraison) + grille de 8 widgets (créées vs terminées 8, tâches par statut, retards, charge par personne, avancement, délai de livraison, jalons à venir, projets actifs) ; états chargement/vide (404 complet)/erreur (+ réessai)/prêt ; note « Données de démonstration fictives ». Route `/projects` branchée sur `RequireModule`.
- i18n `projects.*` FR/EN (`projects.status.*` pour les 4 statuts) ; `src/pages/ProjectsPage.test.tsx` (3 — panneau complet, module non connecté, panne réseau).
- Vérifs : Vitest **42 passed** (12 fichiers) · `npm run lint` ✅ · `npm run typecheck` ✅ · `npm run build` ✅ (avertissement chunk > 500 kB pré-existant).
- Docs : `DECISIONS.md` (décisions 5d), `CHANGELOG.md`, `README.md`, `ARCHITECTURE.md`, ce fichier.
- Commit : `c767cdf`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; sous-phase legal.

### Critères de la phase 5d — vérité du terrain
| Critère | État |
|---|---|
| Tests backend | ✅ suite complète **280 passed** (+12 vs 5c) |
| Tests frontend | ✅ Vitest **42 passed** (12 fichiers) |
| Lint/types backend | ✅ ruff check + format ✅ · mypy strict ✅ (84 fichiers) |
| Lint/types frontend | ✅ `npm run lint` 0 erreur · `npm run typecheck` 0 erreur |
| Build | ✅ `npm run build` OK (avertissement chunk > 500 kB pré-existant) |
| Backend Projets | ✅ `MockProjectsConnector` : 10 séries cohérentes, stock ouvert = différence cumulée, répartitions sommant la métrique parente |
| Frontend Projets | ✅ 4 KPI + 8 widgets, états chargement/vide/erreur, note « données fictives », libellés i18n |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI backend/frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-11 — Sous-phase 5e-a livrée (socle backend du module Identité légale)
Découpage de la 5e (volumineuse) : **5e-a** socle backend (validation + service de registre), **5e-b** persistance et endpoints `legal`, **5e-c** page frontend `/legal`.
- `app/core/siren.py` étendu : `is_valid_siret` (14 chiffres + Luhn) et calcul du numéro de TVA (`french_vat_key` = `(12 + 3 × (SIREN mod 97)) mod 97`, `french_vat_number` = `FR` + clé + SIREN), factorisation d'un `_luhn_is_valid` partagé. L'exception connue de la clé de Luhn (certains établissements de La Poste) est **documentée mais non traitée** faute de règle officielle vérifiée (AGENTS.md §2 : ne rien deviner).
- `app/services/legal_registry.py` : modèle canonique `LegalCompany` (+ `LegalLeader`), contrat `LegalRegistry` (`fetch_by_siren`), et client `RechercheEntreprisesRegistry` de l'API Recherche d'entreprises — `httpx` à **transport injectable** (la CI ne fait jamais d'appel réel), cache mémoire TTL (24 h), timeout 10 s, backoff borné sur 429/5xx (en-tête `Retry-After` respecté, `sleep` injectable). Parsing **tolérant** (`parse_recherche_entreprise`) : champ absent → `None`, entreprise « non diffusible » → dirigeants et adresse masqués (`diffusable=False`). Le mapping des champs (endpoint et noms de clés) est explicitement marqué « à confirmer » sur la documentation officielle avant production.
- Tests : `tests/test_legal_registry.py` (18) — Luhn SIREN/SIRET (cas valides, mauvaise clé, mauvaise longueur, non-chiffres), formule TVA sur exemple figé, parsing complet, SIREN inconnu → `None`, cache (1 seul appel HTTP), non-diffusible, champs optionnels absents, retentative 429 → succès, abandon sur 5xx répétés, erreur cliente définitive, JSON invalide, panne réseau, résultat sans SIREN.
- Vérifs : ruff check + format ✅ · mypy strict ✅ (85 fichiers) · suite backend complète **298 passed** (+18 vs 5d).
- Docs : `DECISIONS.md`, `CHANGELOG.md`, ce fichier.
- Commit : `fcb1c92`.
- **Non fait** : persistance/endpoints (5e-b), page frontend (5e-c) ; push (aucun remote GitHub), merge sur `main` (sans feu vert).

### Critères de la sous-phase 5e-a — vérité du terrain
| Critère | État |
|---|---|
| Tests backend | ✅ suite complète **298 passed** (+18 vs 5d) |
| Lint/types backend | ✅ ruff check + format ✅ · mypy strict ✅ (85 fichiers) |
| Validation légale | ✅ SIRET (Luhn) + clé/n° de TVA calculés ; exception La Poste documentée, non traitée |
| Service registre | ✅ `RechercheEntreprisesRegistry` à transport injectable, cache TTL, timeout, backoff ; aucun appel réseau en test |
| Non diffusible | ✅ dirigeants et adresse masqués (`diffusable=False`) |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI backend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-11 — Sous-phase 5e-b livrée (persistance et endpoints du module Identité légale)
Persistance :
- `app/models/legal_profile.py` : `LegalProfile` (1:1 avec l'organisation, `unique(organization_id)`), colonnes d'identité (`raison_sociale`, `forme_juridique`, `siren`, `siret`, `tva`, `code_naf`, `activite_principale`, `date_creation`, `adresse`, `code_postal`, `ville`, `pays`), adresse/ville, JSONB `dirigeants` (liste) et `field_sources` (provenance par champ), horodatage `synced_at`/`updated_at`. Constantes `LEGAL_PROFILE_TEXT_FIELDS`/`LEGAL_PROFILE_FIELDS`.
- `app/models/legal_identifier.py` : `LegalIdentifier` (unique `(organization_id, pays, schema)`), `IDENTIFIER_SCHEMA_VAT = "vat"` — la TVA étant une donnée d'identifiant (pays + schéma), elle vit ici. `app/models/__init__.py` : exports ajoutés.
- Migration `0007_phase5_legal_profiles_and_rls.py` : 2 tables + index `organization_id` + **RLS** (`ENABLE`/`FORCE` + policy tenant) comme les autres tables métier.
- `app/repositories/legal_profiles.py` (`get_by_organization`, `create`) et `app/repositories/legal_identifiers.py` (`list_for_organization`, `upsert` `pg_insert ... on_conflict_do_update`).
Service et endpoints :
- `app/schemas/legal.py` : `FieldSourceOut`, `LegalDirectorOut`, `LegalIdentifierOut`, `LegalProfileOut`, `LegalDirectorUpdate`, `LegalProfileUpdate` (validators → 422 sur SIREN/SIRET invalides). Le champ JSON `schema` impose un renommage Python `schema_name` + `serialization_alias="schema"` (conflit avec `BaseModel.schema`).
- `app/services/legal.py` : `get_profile` (404 si absente), `update_profile` (saisie manuelle → source `manual` par champ, recalcul de la TVA), `refresh_profile` (interroge le registre par SIREN, fusionne via `_merge_registry_value`, marque la source `registry` + `synced_at`, **le manuel prime** et un écart est consigné ; déduit la TVA depuis le SIREN, dirigeants/adresse masqués si non diffusible). Actions d'audit : `legal.profile.updated`, `legal.profile.refreshed`, `legal.profile.diverged`. Erreurs : 400 (SIREN manquant), 404 (inconnu), 502 (registre injoignable).
- `app/routers/legal.py` : `GET .../legal` (vue), `PUT .../legal` (édition), `POST .../legal/refresh` (édition, rafraîchit depuis le registre). Les **dirigeants ne sont exposés qu'à l'admin**. `app/core/deps.py` : `get_legal_registry`. `app/main.py` : `RechercheEntreprisesRegistry` posé sur `app.state.legal_registry` et router monté.
Tests :
- `tests/test_legal.py` (19) : lecture admin/membre, `view` lit mais n'écrit pas → 403, `edit` écrit, saisie manuelle → source `manual`, NAF/TVA calculés, validation 422, rafraîchissement qui pré-remplit, sans SIREN → 400, inconnu → 404, registre indisponible → 502, le manuel prime + `legal.profile.diverged`, changement du registre → champ mis à jour + 2 × `legal.profile.refreshed`, non diffusible masque adresse et dirigeants, dirigeants masqués hors admin, autre organisation → 403, isolation RLS directe (db_session).
- `tests/conftest.py` : `TRUNCATE` étendu. `tests/helpers.py` : `SIREN_VALIDE`/`SIRET_VALIDE`, `sample_company`, `FakeLegalRegistry`, `install_legal_registry`. `tests/test_alembic.py` : `HEAD_REVISION = "0007"`, `TENANT_TABLES` += 2.
- **Pièges résolus** : conflit Pydantic `schema` (renommage `schema_name`) ; corruption UTF-8 de `test_legal.py` par PowerShell (réécriture via l'outil d'écriture, BOM retiré par `ruff format`) — leçon : ne pas éditer les sources accentuées avec `Set-Content`/`Get-Content`.
- Vérifs : ruff check + format ✅ · mypy strict ✅ (92 fichiers) · `pytest tests/test_legal.py tests/test_alembic.py` **26 passed** · suite backend complète **316 passed** (+18 vs 5e-a) — un test *flaky* préexistant (`tests/connectors/test_scheduler.py`) vert en exécution isolée.
- OpenAPI : non régénéré ici, reporté à la 5e-c (couplé au frontend).
- Commit : `eb821a4 feat: add legal identity persistence and endpoints (phase 5e-b)` (15 fichiers, +1378/−2).
- **Non fait** : page frontend (5e-c) ; push (aucun remote GitHub), merge sur `main` (sans feu vert).

### Critères de la sous-phase 5e-b — vérité du terrain
| Critère | État |
|---|---|
| Tests backend | ✅ suite complète **316 passed** (+18 vs 5e-a) |
| Lint/types backend | ✅ ruff check + format ✅ · mypy strict ✅ (92 fichiers) |
| Persistance | ✅ `legal_profiles` + `legal_identifiers`, migration `0007` RLS (tenant isolé, test dédié) |
| Endpoints | ✅ `GET`/`PUT`/`POST refresh` sous `/organizations/{id}/legal`, gardes `view`/`edit`, dirigeants admin only |
| Provenance par champ | ✅ source `registry`/`manual` + date, le manuel prime et l'écart est journalisé |
| pre-commit | ⏳ à lancer avant commit |
| CI backend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-11 — Sous-phase 5e-c livrée (page frontend de la Fiche légale)
- Nouveau dossier `src/legal/` (hors `src/metrics/` : la fiche est un objet unique, sans polling, v. `DECISIONS.md`) : `queries.ts` (`legalKeys`, `fetchLegalProfile`, `useLegalProfile`, `useUpdateLegalProfile` (PUT) et `useRefreshLegalProfile` (POST refresh) qui mettent à jour le cache TanStack Query), `mentions.ts` (12 champs texte dans l'ordre d'affichage, `formatDate`/`formatDateTime` via `Intl`, `vatIdentifier`, `hasAnyData`, `buildMentionsText`), `ProvenanceBadge.tsx` (source `registry`/`manual`/`computed` + date de synchro), `LegalEditForm.tsx` (saisie des 12 champs + dirigeants admin ; n'envoie **que** les champs réellement modifiés pour préserver la provenance des champs inchangés).
- `src/pages/LegalPage.tsx` (`/legal`, gardée par `RequireModule moduleKey="legal"`) : en-tête avec actions rafraîchir/éditer limitées au niveau `edit` ou au rôle admin ; quatre blocs — identité avec provenance par champ, TVA, dirigeants (**visibles des seuls administrateurs**), bloc « mentions légales » copiable en un clic (`navigator.clipboard`) ; export PDF par `window.print()` ; états chargement (squelette)/vide/erreur (+ réessai). Une modification n'est pas permise à un membre `view` (aucun bouton d'édition) et les dirigeants sont masqués hors admin.
- Câblage : `src/app/routes.tsx` pointe `/legal` sur `LegalPage` (fin des placeholders) ; `src/api/types.ts` ajoute `LegalProfile`/`LegalProfileUpdate`/`LegalDirector`/`LegalIdentifier`/`LegalFieldSource` (alias du schéma généré) ; i18n `legal.*` FR/EN ; régénération du client OpenAPI (`schema.json` + `schema.d.ts`) ; suppression de `src/pages/ModulePage.tsx` (devenu mort).
- Tests : `src/pages/LegalPage.test.tsx` (4 — fiche complète avec provenance/dirigeants/mentions, dirigeants et actions masqués pour un membre, panne réseau avec réessai, saisie manuelle n'envoyant que le champ modifié).
- Vérifs : Vitest **46 passed** (13 fichiers, +4 vs 5d) · `npm run lint` 0 erreur · `npm run typecheck` 0 erreur · `npm run build` OK · `export_openapi.py` sans diff (schéma à jour) · suite backend complète **317 passed** (209 s ; la 5e-c ne touche pas au backend).
- Docs : `DECISIONS.md` (5 décisions : dossier `legal/`, export PDF par impression du navigateur, envoi sélectif des champs, comptage client des champs modifiés au refresh, suppression de `ModulePage`), `CHANGELOG.md`, `README.md`, `ARCHITECTURE.md`, ce fichier.
- Commit : `206a0c7 feat: add legal identity page (phase 5e-c)` ; docs dans le commit suivant.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; sous-phase 5f « Pouls ».

### Critères de la sous-phase 5e-c — vérité du terrain
| Critère | État |
|---|---|
| Tests frontend | ✅ Vitest **46 passed** (13 fichiers) |
| Tests backend | ✅ suite complète **317 passed** (la 5e-c n'ajoute aucun test backend) |
| Lint/types frontend | ✅ `npm run lint` 0 erreur · `npm run typecheck` 0 erreur |
| Build | ✅ `npm run build` OK (avertissement chunk > 500 kB pré-existant) |
| Client OpenAPI | ✅ `export_openapi.py` régénéré sans diff (`schema.json` + `schema.d.ts` à jour) |
| Fiche légale | ✅ 12 champs + provenance par champ, TVA, dirigeants (admin), mentions copiables, export PDF, saisie sélective |
| Permission `legal` | ✅ `view` lit sans bouton d'édition ; `edit`/admin rafraîchissent et modifient ; dirigeants masqués hors admin |
| Routes | ✅ `/legal` sur `LegalPage` ; plus aucun placeholder `ModulePage` |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI backend/frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-12 — Sous-phase 5f livrée (Vue d'ensemble « Pouls » — backend + frontend)
Périmètre (décision) : **minimal** — KPI clés des modules autorisés + santé **opérationnelle** + fil d'activité + carte Objectifs vide ; les alertes et objectifs métier réels viendront en phase 6.
Backend :
- `app/schemas/pulse.py` : `PulseKpiOut` (module, `metric_key`, unité, valeur, `previous_value` pour la tendance, horodatage), `PulseHealthOut` (`status` `good`/`warning`/`unknown`, `modules_with_data`, `modules_total`) et `PulseOut` (kpis, health, activity).
- `app/services/pulse.py` : `PULSE_KPI_KEYS` (8 clés — `finance.revenue`/`margin`, `web.visitors`/`conversions`, `social.followers`/`engagement_rate`, `projects.open_tasks`/`avg_progress` ; le légal, sans métrique, est exclu) et `build_pulse` — restreint chaque KPI aux modules visibles (`modules_for`), **omet** un KPI sans donnée (jamais de valeur inventée), calcule la santé (`good` si tous les modules visibles à KPI ont de la donnée, `warning` sinon, `unknown` si aucun) et n'ajoute le fil d'activité (`services.audit.list_recent`) que pour un administrateur.
- `app/routers/pulse.py` : `GET /organizations/{organization_id}/pulse` — **pas de garde de module** (la route restreint elle-même par membre) ; un membre sans module reçoit un Pouls vide, jamais un 403. Monté dans `app/main.py`.
- `app/repositories/metric_snapshots.py` : nouvelle lecture `get_latest` (du plus récent au plus ancien) pour la valeur courante **et** la précédente (`get_series` trie en ordre croissant).
- Tests : `tests/test_pulse.py` (7 — Pouls admin complet, KPI d'un module non autorisé omis, santé `good`/`warning`/`unknown`, KPI sans donnée omis, fil d'activité admin/membre, tendance).
- Vérifs : `pytest tests/test_pulse.py` **7 passed** · suite backend complète **324 passed** (214,91 s) · ruff check + format ✅ · mypy strict ✅ (95 fichiers).
Frontend (page d'accueil `/`, le tableau de bord placeholder est remplacé) :
- `src/pulse/queries.ts` (`usePulse`, polling 5 min, `retry:false`) et `src/pulse/format.ts` (`KPI_META` réutilisant les libellés i18n des modules, `kpiTrend`, `formatRelativeTime` via `Intl.RelativeTimeFormat`, `actionLabelKey` des actions d'audit).
- `src/pages/DashboardPage.tsx` réécrit : grille de `KpiCard` (les KPI clés autorisés), badge de santé en en-tête (`role="status"`), panneau d'activité (note « réservée aux administrateurs » sinon) et carte « Objectifs » en état vide ; suppression des panneaux d'accueil/accès rapide et des 4 `ChartCard` placeholder ; états chargement (squelette)/erreur (+ réessai).
- `src/api/types.ts` : alias `Pulse`/`PulseKpi`/`PulseHealth`/`AuditLog` ; i18n `dashboard.*` FR/EN (libellés de module réutilisés) + `common.percent` + `web.kpiConversions`/`web.unitConversions` ; régénération du client OpenAPI (`schema.json` + `schema.d.ts`).
- Tests : `src/pages/DashboardPage.test.tsx` (4 — Pouls complet admin, membre sans activité, KPI vides, panne réseau) ; `App.test.tsx` et `e2e/helpers.ts` mockent `/pulse` ; e2e Playwright `login.spec.ts` (assertion du titre d'accueil mise à jour en `Vue d'ensemble`) et `a11y.spec.ts`.
- Vérifs : Vitest **50 passed** (14 fichiers) · `npm run lint` 0 erreur · `npm run typecheck` 0 erreur · `npm run build` OK (avertissement chunk > 500 kB pré-existant).
- Vérifs e2e : `npx playwright test` **5 passed** — une assertion de `login.spec.ts` était restée sur l'ancien titre (« Bienvenue sur votre tableau de bord ») : corrigée (`a6f9c96`), ce que la suite Vitest ne pouvait pas détecter.
- Docs : `DECISIONS.md` (6 décisions 5f), `CHANGELOG.md`, `README.md`, `ARCHITECTURE.md`, ce fichier.
- Commit : `a1d65e1 feat: add overview pulse page and aggregate endpoint (phase 5f)` · correctif e2e `a6f9c96` ; docs dans le commit suivant (`479ca93`).
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; clôture de la phase 5 et phase 6.

### Critères de la sous-phase 5f — vérité du terrain
| Critère | État |
|---|---|
| Tests backend | ✅ `tests/test_pulse.py` **7 passed** · suite complète **324 passed** (+7 vs 5e-c) |
| Tests frontend | ✅ Vitest **50 passed** (14 fichiers, +4 vs 5e-c) |
| Lint/types backend | ✅ ruff check + format ✅ · mypy strict ✅ (95 fichiers) |
| Lint/types frontend | ✅ `npm run lint` 0 erreur · `npm run typecheck` 0 erreur |
| Build | ✅ `npm run build` OK (avertissement chunk > 500 kB pré-existant) |
| e2e Playwright | ✅ `npx playwright test` **5 passed** (login 3 + a11y 2) |
| Endpoint Pouls | ✅ `GET /organizations/{id}/pulse` : 8 KPI clés restreints aux modules visibles, santé opérationnelle, activité admin-only |
| Frontend Pouls | ✅ page d'accueil réécrite : KPI + badge de santé + fil d'activité + objectifs vides, états chargement/erreur, i18n FR/EN |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI backend/frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-12 — Clôture de la phase 5 (Modules MVP, 5a → 5f)
- Critères AGENTS.md §3 remplis : suite backend **324 tests verts**, Vitest **50 passed** (14 fichiers), e2e Playwright **5 passed**, ruff + ruff format + mypy strict (95 fichiers) OK, `npm run lint`/`typecheck`/`build` OK, pre-commit **11 hooks** (gitleaks — aucun secret), docs à jour (README, ARCHITECTURE, DECISIONS, PROGRESS, CHANGELOG).
- Corrections en route : `login.spec.ts` restait sur l'ancien titre d'accueil (« Bienvenue sur votre tableau de bord » → `Vue d'ensemble`) après la réécriture de `DashboardPage` ; Vitest ne voyait pas cette assertion, seul l'e2e l'a signalée (`a6f9c96`).
- Décisions consignées dans `docs/DECISIONS.md` au fil des sous-phases (Recharts et les 8 clés finance, répartitions web/social/projets sommant la métrique parente, abonnés cumulés, stock de tâches ouvertes, registre légal à transport injectable, provenance par champ, Pouls minimal).
- Merge sur `main` : `git merge --no-ff phase-5-modules-mvp` → `dcb7c9d` (`main` passe de `cc840c9` à `dcb7c9d`) ; aucun push (aucun remote GitHub configuré).
- **Non fait** : push (aucun remote GitHub) ; phase 6 « Fonctions transverses » à ouvrir sur une nouvelle branche.

## Phase 6 — Fonctions transverses

### 2026-10-12 — Sous-phase 6a-i : comparaison de périodes (backend)
- Catalogue d'agrégation `app/services/metric_catalog.py` : chaque clé connue → `sum` (flux), `last` (niveau/stock), `average` (taux/durée) ; repli `sum` pour une clé inconnue. Test de couverture : toute clé produite par les quatre connecteurs doit y figurer (aucune omission silencieuse).
- Schémas `MetricAggregation`/`MetricComparisonSummary`/`MetricComparison` ; service `metrics.get_metric_comparison` (une seule lecture de la double fenêtre `[end − 2×days, end]`, frontière `end − days`) ; route `GET /organizations/{id}/metrics/{metric_key}/comparison?days=&end=`.
- Tests : `tests/test_metric_catalog.py` (8) + `tests/connectors/test_metric_comparison.py` (10) — répartition des fenêtres, somme/dernière valeur/moyenne, écart et pourcentage (`null` si base nulle), jours hors bornes, 403 droits/organisation, 422 clé, 404 sans donnée.
- Client OpenAPI régénéré (`schema.json` + `schema.d.ts`).
- Commit : `4c41e9e` — `feat: comparaison de periodes par metrique (6a-i)`.
- **Non fait** : sélecteur de période et affichage frontend (6a-ii) ; objectifs/budgets avec alertes (6a-iii/iv).

### Critères de la sous-phase 6a-i — vérité du terrain
| Critère | État |
|---|---|
| Tests backend (sous-phase) | ✅ `tests/test_metric_catalog.py` **8 passed** · `tests/connectors/test_metric_comparison.py` **10 passed** |
| Suite backend complète | ✅ `pytest -q` **342 passed** (22 min 33 s ; suite DB lourde) |
| Lint/types backend | ✅ `ruff check` + `ruff format --check` ✅ · `mypy` strict **96 fichiers**, 0 erreur |
| Frontend | ✅ `tsc -b` ✅ · `eslint` ✅ · Vitest **14 fichiers / 50 tests passed** |
| Schéma OpenAPI | ✅ `export_openapi.py` + `generate:api` régénérés |

### 2026-10-12 — Sous-phase 6a-ii : sélecteur de période et comparaison (frontend)
- Composant `src/components/ui/PeriodSelect.tsx` : groupe de boutons accessible (`role="group"`, `aria-pressed`, anneau de focus), sans état interne — même patron que `LanguageSwitcher`. Constantes `PERIOD_OPTIONS` (7 j / 30 j / 90 j) et `DEFAULT_PERIOD_DAYS` dans `src/metrics/queries.ts`.
- `src/metrics/queries.ts` : clé de cache `metricsKeys.comparison` et fonction `fetchMetricComparison(organizationId, metricKey, days)` (endpoint `GET /metrics/{clé}/comparison`), plus les alias de types `MetricAggregation`/`MetricComparison`/`MetricComparisonSummary` (`src/api/types.ts`).
- `src/pages/DashboardPage.tsx` : sélecteur de période au-dessus de la grille de KPI (masqué sans donnée) ; `useQueries` déclenche une comparaison par KPI visible (clés dérivées du Pouls), la carte affiche l'agrégat de la fenêtre (`summary.current_value`) et l'écart `change_percent` ; un 404 « aucune donnée sur la fenêtre » retombe sur la valeur et la tendance à deux points du Pouls, jamais sur une erreur. i18n `dashboard.periodLabel`/`dashboard.periodDays` (FR/EN).
- Tests : `src/components/ui/PeriodSelect.test.tsx` (1) + `src/pages/DashboardPage.test.tsx` (5, dont un test de comparaison : valeur/écart de la période, défaut 30 j, bascule vers 7 j) ; route de comparaison simulée dans le stub (404 = pas de donnée). Aucun changement e2e (le Pouls simulé n'expose aucun KPI).
- Vérifs : Vitest **52 passed** (15 fichiers, +2 vs 6a-i) · `tsc -b` ✅ · `eslint` ✅ · `npm run build` ✅ · `npx playwright test` **5 passed** · pas de changement backend.
- Commit : `01c2220` — `feat: selecteur de periode et comparaison sur le tableau de bord (6a-ii)`.
- **Non fait** : objectifs/budgets avec alertes (6a-iii/iv).

### Critères de la sous-phase 6a-ii — vérité du terrain
| Critère | État |
|---|---|
| Tests frontend (sous-phase) | ✅ `PeriodSelect.test.tsx` **1 passed** · `DashboardPage.test.tsx` **5 passed** |
| Suite frontend complète | ✅ Vitest **52 passed** (15 fichiers, +2 vs 6a-i) |
| Lint/types frontend | ✅ `npm run typecheck` (`tsc -b`) ✅ · `npm run lint` (ESLint) 0 erreur |
| Build | ✅ `npm run build` OK (avertissement « chunk > 500 kB » préexistant) |
| e2e Playwright | ✅ `npx playwright test` **5 passed** (login 3 + a11y 2) |
| Sélecteur de période | ✅ 7 j / 30 j / 90 j, défaut 30 j, accessible (`role="group"`, `aria-pressed`) |
| Comparaison affichée | ✅ valeur = `summary.current_value`, écart = `summary.change_percent` ; repli sur la dernière valeur du Pouls si 404/chargement |
| i18n | ✅ `dashboard.periodLabel` / `dashboard.periodDays` FR + EN, aucun texte en dur |
| pre-commit | ⏳ à lancer avant commit |
| CI frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-12 — Sous-phase 6a-iii : objectifs & budgets (backend)
- Persistance : `app/models/goal.py` — table tenant `goals` (`metric_key` canonique, `label` libre optionnel, `direction`, `target_value`, `period_days` 1–365) + contraintes `CHECK` (`goals_key_format` sur `METRIC_KEY_REGEX`, `goals_direction_known`, `goals_period_days_range`) ; `app/models/enums.py` gagne `GoalDirection` (`at_least`/`at_most`) et `GOAL_DIRECTION_VALUES_SQL` ; migration `0008_phase6_goals_and_rls.py` (table + index `organization_id` + RLS `ENABLE`/`FORCE` + politique par organisation).
- Couche service : `app/repositories/goals.py` (`list_for_organization`, `get_by_id`, `create`, `delete`) ; `app/schemas/goals.py` : `GoalStatus` (`achieved`/`on_track`/`off_track`/`unknown`), `GoalCreate`, `GoalUpdate` (mise à jour partielle via `model_fields_set` ; `label: null` efface), `GoalOut` ; `app/services/goals.py` (progression recalculée à la lecture) ; `app/routers/goals.py`.
- Progression/dérive (SPEC muette — règle documentée dans `DECISIONS.md`) : progression = valeur agrégée de la fenêtre courante / cible (`progress_percent`, `null` si cible nulle) ; statut `achieved` (cible atteinte), `off_track` (non atteinte **et** métrique s'éloignant de la fenêtre précédente équivalente), `on_track`, `unknown` (aucune donnée). La réduction de fenêtre est factorisée dans `metric_catalog.reduce_values` (même code que `metrics._aggregate`) — aucune divergence entre comparaison (6a-i) et objectifs.
- Endpoints `GET`/`POST` (201)/`PATCH`/`DELETE` (204) `/organizations/{id}/goals` : la lecture ne montre que les objectifs des modules visibles (comme le Pouls, jamais de 403) ; créer/modifier/supprimer exige `edit` sur le module préfixe de `metric_key` (vérifié dans le service) ; audit `goal.created`/`goal.updated`/`goal.deleted`.
- Tests : `tests/test_goals.py` (15) — `achieved`, `on_track`/`off_track` selon la direction, `at_most` (budget), `unknown` sans donnée, `progress_percent` (`null` si cible nulle), 422 clé/`period_days`/direction, 403 droits et module, 404 objectif absent, lecture restreinte aux modules visibles, audit des trois actions, isolation RLS entre deux organisations. `tests/test_alembic.py` (`HEAD_REVISION` = `0008`, `TENANT_TABLES` += `goals`) et `tests/conftest.py` (TRUNCATE) mis à jour.
- Client OpenAPI régénéré (`schema.json` + `schema.d.ts` : opérations `list_/create_/update_/delete_goal` et schémas `GoalCreate`/`GoalUpdate`/`GoalOut`/`GoalStatus`).
- Commit : `831546e` — `feat: objectifs et budgets avec alerte de derive (6a-iii)`.
- **Non fait** : frontend objectifs (6a-iv) ; push (aucun remote GitHub), merge sur `main` (sans feu vert).

### Critères de la sous-phase 6a-iii — vérité du terrain
| Critère | État |
|---|---|
| Tests backend (sous-phase) | ✅ `tests/test_goals.py` **15 passed** |
| Suite backend complète | ✅ `pytest -q` **357 passed** (299 s, +15 vs 6a-i) |
| Lint/types backend | ✅ `ruff check` + `ruff format --check` ✅ · `mypy` strict **101 fichiers**, 0 erreur |
| Persistance | ✅ table `goals` + migration `0008` ; RLS activée/forcée, isolation testée entre deux organisations |
| Endpoints | ✅ `GET`/`POST`/`PATCH`/`DELETE /organizations/{id}/goals`, gardés par le module de la métrique, audit `goal.*` |
| Progression & dérive | ✅ agrégation via `metric_catalog.reduce_values` ; statut `achieved`/`on_track`/`off_track`/`unknown` |
| Entrées | ✅ clé canonique (422), `period_days` 1–365, `direction` `at_least`/`at_most` |
| Schéma OpenAPI | ✅ `export_openapi.py` + `generate:api` régénérés |
| Frontend | ✅ `tsc -b` ✅ · `eslint` ✅ (aucun changement de code frontend, seulement le client généré) |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI backend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-13 — Sous-phase 6a-iv livrée (objectifs & budgets côté frontend)
- Nouvel emplacement `src/goals/` : `GoalsPanel` (carte du tableau de bord à côté du fil d'activité, remplace l'état vide de la 5f), `GoalForm` (création **et** édition), `queries.ts` (`useGoals` + mutations `useCreateGoal`/`useUpdateGoal`/`useDeleteGoal` vers `POST`/`PATCH`/`DELETE` ; 204 contrôlé à la main pour la suppression, toute écriture invalide la liste) et `format.ts` (métadonnées des statuts i18n + teintes de badge/barre, options d'indicateur, droits d'écriture).
- Affichage : nom (libellé ou nom du KPI ciblé), sens + cible unitée + fenêtre, progression (barre `role="progressbar"` + pourcentage, « sans donnée » si `progress_percent` nul) et statut `achieved`/`on_track`/`off_track`/`unknown` recalculés par le backend — la dérive (`off_track`) est mise en évidence en rouge (badge + barre). i18n `goals.*` FR/EN, aucun texte en dur (AGENTS.md §7, §8).
- Droits : les actions créer/modifier/supprimer ne s'affichent qu'avec le droit d'écriture sur le module de l'indicateur (`canEditMetric` : admin = tout, sinon `edit`) ; la suppression demande confirmation (`window.confirm`) ; le masquage n'est qu'un confort d'interface, le backend applique seul la règle (6a-iii).
- Formulaire : sélecteur d'indicateur **limité aux 8 KPI clés du Pouls** (`KPI_META`, libellés i18n réutilisés — une clé existante hors liste reste éditable), sens `at_least`/`at_most`, cible (nombre), fenêtre via `PeriodSelect` partagé (7/30/90 j, défaut 30), libellé optionnel (max 120).
- Tests : 5 cas dans `DashboardPage.test.tsx` (affichage progression/statut, création avec retombée i18n du nom, édition PATCH, suppression DELETE après confirmation, actions masquées pour un membre en `view`) ; route `/goals` simulée (y compris `/goals/{id}` PATCH/DELETE) dans `App.test.tsx` et les mocks e2e.
- Vérifs : Vitest **57 passed** (15 fichiers, +5 vs 6a-ii/iii) · `npm run typecheck` 0 erreur · `npm run lint` 0 erreur · `npm run build` OK (avertissement « chunk > 500 kB » préexistant) · `npx playwright test` **5 passed** · pre-commit ✅ (gitleaks inclus) · aucun changement backend ni régénération OpenAPI.
- Commit : `e114627` — `feat: objectifs et budgets cote frontend (6a-iv)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; sous-phase 6b.
- *Écart constaté : `DashboardPage.test.tsx` ne compilait pas (`waitFor` non importé) — corrigé avant exécution.*

### Critères de la sous-phase 6a-iv — vérité du terrain
| Critère | État |
|---|---|
| Tests frontend | ✅ Vitest **57 passed** (15 fichiers, +5 vs 6a-ii/iii) |
| Lint/types frontend | ✅ `npm run typecheck` (`tsc -b`) ✅ · `npm run lint` 0 erreur |
| Build | ✅ `npm run build` OK (avertissement « chunk > 500 kB » préexistant) |
| e2e Playwright | ✅ `npx playwright test` **5 passed** (mocks `/goals` ajoutés) |
| Panneau d'objectifs | ✅ liste + progression + statut (dérive en évidence), création/édition/suppression, actions selon le droit d'écriture du module |
| i18n | ✅ `goals.*` FR + EN, aucun texte en dur ; libellés d'indicateur réutilisés du Pouls |
| Backend | ✅ inchangé (client OpenAPI à jour) |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-13 — Sous-phase 6b-i livrée (recherche globale Ctrl/Cmd+K)
- Découpage de la 6b (volumineuse) en deux : **6b-i** recherche globale (SPEC §4, frontend seul) et **6b-ii** dashboard personnalisable (backend `dashboard_layouts` + widgets déplaçables/redimensionnables, à venir).
- `src/search/items.ts` : index de recherche dérivé du **catalogue statique** de l'application (routes des modules + `KPI_META` du Pouls), filtré par les permissions courantes (`canSeeModule`, Équipe réservée aux admins) ; `normalizeText` (casse + accents, NFD) et `searchItems` (sous-chaîne sur le libellé **et** la ligne secondaire, bornée à 8). Un KPI navigue vers son module porteur ; « projets/tâches » sont couverts par la page et les KPI projets (aucune entité tâche dans le produit — décision notée).
- `src/search/SearchPalette.tsx` : palette contrôlée par l'`AppShell` (props `open`/`onOpen`/`onClose`/`permissions`) — **Ctrl/Cmd+K** bascule, Échap ferme, focus déplacé sur la recherche à l'ouverture et rendu à l'élément précédent à la fermeture ; navigation flèches + Entrée ou clic (motif combobox accessible : `role="dialog"`/`combobox`/`listbox`/`option`, `aria-activedescendant`, `aria-selected`). Bouton « Rechercher » (icône + `kbd` « Ctrl K ») dans la `Topbar`.
- i18n `search.*` FR/EN ; aucun backend, aucune régénération OpenAPI, aucune donnée d'API (index statique + permissions).
- Tests : `items.test.ts` (8 — couverture admin/membre/null, filtrage casse/accents/ligne secondaire, limite) + `SearchPalette.test.tsx` (5 — Ctrl+K/Échap, filtre + Entrée, flèches, clic, permissions) ; e2e `search.spec.ts` (2 — Ctrl+K réel + bouton topbar).
- Vérifs : Vitest **70 passed** (17 fichiers, +13 vs 6a-iv) · `npm run typecheck` 0 erreur · `npm run lint` 0 erreur · `npm run build` OK (avertissement « chunk > 500 kB » préexistant) · `npx playwright test` **7 passed** (a11y du dashboard inclus, aucune violation sérieuse) · pre-commit ✅ 11 hooks Passed (gitleaks inclus) · aucun changement backend.
- Commit : `bd6dcbf` — `feat: recherche globale Ctrl/Cmd+K (6b-i)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; à suivre : **6b-ii**.

### Critères de la sous-phase 6b-i — vérité du terrain
| Critère | État |
|---|---|
| Tests frontend | ✅ Vitest **70 passed** (17 fichiers, +13 : 8 `items.test.ts` + 5 `SearchPalette.test.tsx`) |
| Tests e2e | ✅ `npx playwright test` **7 passed** (+2 `search.spec.ts` ; a11y du dashboard scanné avec le nouveau bouton) |
| Lint/types frontend | ✅ `npm run typecheck` (`tsc -b`) ✅ · `npm run lint` 0 erreur |
| Build | ✅ `npm run build` OK (avertissement « chunk > 500 kB » préexistant) |
| Raccourci | ✅ Ctrl/Cmd+K bascule la palette, Échap ferme ; bouton « Rechercher » (avec kbd) dans la topbar |
| Index | ✅ pages (modules filtrés + Équipe admin + paramètres) + 8 KPI clés, filtrage insensible casse/accents, « projets/tâches » couverts par la page et les KPI projets |
| i18n | ✅ `search.*` FR + EN, aucun texte en dur (kbd « Ctrl K » = nom de touche, convention non traduite, v. `DECISIONS.md`) |
| Backend | ✅ inchangé (aucune API : l'index est statique, filtré par les permissions courantes) |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI frontend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-14 — Sous-phase 6b-ii-a livrée (persistance de la mise en page, backend)
- Découpage de la 6b-ii en deux : **6b-ii-a** persistance de la mise en page (backend, SPEC §4, cette sous-phase) et **6b-ii-b** widgets déplaçables/redimensionnables (frontend, à venir).
- Table tenant `dashboard_layouts` (migration Alembic `0009`, RLS activée et forcée + politique par organisation) — une ligne par couple `(organization_id, user_id)` (contrainte d'unicité), disposition en JSONB (`widgets` = liste de placements `{widget_id, x, y, w, h}`, contrainte `jsonb_typeof = 'array'`). `app/models/dashboard_layout.py`, `app/repositories/dashboard_layouts.py` (`get_for_user`, `upsert` ON CONFLICT, `delete_for_user` avec `RETURNING`).
- `app/services/dashboard.py` porte le **catalogue** de widgets (`health`, KPI `kpi.<clé canonique>` des modules visibles — mêmes règles que le Pouls via `modules_for`, `goals`, fil d'activité `activity` réservé aux admins) et la **disposition par défaut** (santé en bandeau, KPI par trois, objectifs + activité côte à côte) ; aucun libellé composé côté backend.
- Endpoints `GET`/`PUT`/`DELETE /api/v1/organizations/{id}/dashboard` (`app/routers/dashboard.py`, `app/schemas/dashboard.py`) : la mise en page est **personnelle** (aucun droit de module exigé), le `GET` renvoie `available_widgets` + `layout` (enregistrée ou par défaut, `is_default`), le `PUT` remplace la disposition du membre (widget inconnu → 422, widget non autorisé → 403, doublon → 422, `x + w > 12` ou hauteur hors bornes → 422), le `DELETE` restaure le défaut ; audit `dashboard.layout.updated`/`reset` (journalisé seulement si une disposition existait). À la lecture, un widget enregistré puis devenu interdit est écarté (défense en profondeur).
- Grille fixée au schéma : `GRID_COLUMNS = 12`, `MAX_WIDGET_HEIGHT = 24`, `MAX_WIDGETS = 24` (partagés avec `react-grid-layout` en 6b-ii-b).
- Client OpenAPI régénéré (`schema.json` + `schema.d.ts` : opérations `read_dashboard`/`save_dashboard`/`reset_dashboard` et schémas `DashboardOut`/`DashboardWidgetOut`/`DashboardPlacement`/`DashboardLayoutUpdate`/`WidgetKind`).
- Tests : `tests/test_dashboard.py` (14) — défaut admin, catalogue filtré par module (finance), description du catalogue (genre/module/clé), enregistrement + relecture + audit, remise à zéro + audit, disposition propre à chaque utilisateur, widget inconnu (422), doublon (422), bornes de grille (422), activité interdite à un membre (403), module invisible (403), filtrage à la lecture d'un widget devenu interdit, 403 hors organisation, isolation RLS.
- Vérifs : suite backend **371 passed** (+14, 387 s) · `ruff check`/`ruff format --check` OK · `mypy` 0 erreur · `tests/test_alembic.py` mis à jour (`HEAD_REVISION = "0009"`, `dashboard_layouts` dans `TENANT_TABLES`) · `frontend/openapi/schema.json` régénéré sans diff de type · `npm run typecheck`/`npm run lint` 0 erreur.
- Commit : `3f26777` — `feat: persistance de la mise en page du tableau de bord (6b-ii-a)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; 6b-ii-b (frontend) à suivre.

### Critères de la sous-phase 6b-ii-a — vérité du terrain
| Critère | État |
|---|---|
| Tests backend | ✅ pytest **371 passed** (dont 14 `test_dashboard.py`) |
| Migrations | ✅ `test_alembic.py` (aller-retour `0001`→`0009`, RLS activée/forcée sur `dashboard_layouts`, `HEAD_REVISION = "0009"`) |
| Lint/types backend | ✅ `ruff check` + `ruff format --check` OK · `mypy` 0 erreur |
| Client OpenAPI | ✅ `export_openapi.py` + `generate:api` régénérés (`schema.json` + `schema.d.ts`) |
| Isolation tenant | ✅ test RLS dédié (une organisation ne voit pas les dispositions d'une autre) |
| Permissions | ✅ catalogue filtré (KPI des modules visibles, activité admin) ; écriture refusée 422/403 ; lecture filtrée (défense en profondeur) |
| Audit | ✅ `dashboard.layout.updated` / `dashboard.layout.reset` |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI backend | ⚠️ job écrit, pas d'exécution (aucun remote GitHub) |

### 2026-10-14 — Sous-phase 6b-ii-b livrée (tableau de bord personnalisable, frontend)
- Découpage retenu : **6b-ii-b** = le rendu frontend de la disposition écrite en 6b-ii-a (widgets déplaçables/redimensionnables). `react-grid-layout@2.3.0` est installé épinglé (`--save-exact`) — version stable vérifiée sur npm, réécriture TypeScript (points d'entrée `core`/`extras`/`legacy`/`react`/`responsive`), **aucune feuille de style livrée** (styles en ligne).
- Nouveau dossier `src/dashboard/` : `layout.ts` (fonctions pures `toGridLayout`/`toPlacements`/`sameLayout`/`widgetTitleKey` + constantes `GRID_COLUMNS = 12`, `ROW_HEIGHT = 40`, `GRID_MARGIN = [16, 16]`, bornes alignées sur le backend), `widgets.tsx` (registre de rendu par genre — `HealthWidget`/`KpiWidget`/`GoalsPanel`/`ActivityWidget` — et type `WidgetData` assemblé une fois par la page), `DashboardGrid.tsx` (enveloppe `GridLayout`, largeur mesurée localement : `clientWidth` + `ResizeObserver` si présent, repli sur l'événement `resize`, largeur par défaut 1200 px) et `queries.ts` (`useDashboard`/`useSaveDashboard`/`useResetDashboard` → `GET`/`PUT`/`DELETE /organizations/{id}/dashboard`, écriture par mutation, remise à zéro par invalidation).
- `DashboardPage` réécrite : la page ne compose plus une grille figée mais rend **la disposition servie par l'API** (items `i` = `widget_id`, mêmes unités de grille que le serveur, un widget absent du catalogue est ignoré). En lecture la grille est immobile ; le bouton « Personnaliser » ouvre le mode édition (poignée de déplacement `.widget-handle` par widget, redimensionnement par le coin bas-droit, boutons Enregistrer/Annuler/Réinitialiser). Le brouillon local n'est créé qu'au premier changement réel (`sameLayout`), toute nouvelle disposition serveur le réinitialise ; la comparaison de périodes et le panneau d'objectifs sont conservés tels quels (seuls les widgets KPI portent le sélecteur).
- Décision : **aucune garde d'activité côté client** — le backend écarte `activity` du catalogue des non-admins et filtre la disposition enregistrée à la lecture (un seul arbitre des droits, le serveur) ; le composant ne revérifie donc pas le rôle (code mort évité).
- i18n `dashboard.*` FR/EN complété (`healthTitle`, `customize`, `editHint`, `save`, `cancel`, `reset`, `kpiNoData`) ; suppression des clés `activityAdminOnly*` (devenues inutiles — le fil n'est plus jamais servi à un membre).
- Tests : `layout.test.ts` (8 — conversion aller/retour, tri déterministe, comparaison par identifiant, clés i18n) ; `DashboardPage.test.tsx` réécrit (12 cas, dont **enregistrement de la disposition** — corps du `PUT` vérifié — et **remise à zéro** — `DELETE` vérifié ; le stub `/dashboard` reproduit le catalogue et la disposition par défaut du backend, filtrés par rôle) ; e2e `dashboard.spec.ts` (2 — affichage piloté par la disposition, puis **déplacement réel** d'un widget à la souris → `PUT` reflétant le déplacement → `DELETE`).
- Outillage : délai des requêtes asynchrones de test porté à 5 s (`configure({ asyncUtilTimeout: 5000 })` dans `src/test/setup.ts`) — les pages à graphiques (Recharts sous jsdom) dépassaient le défaut de 1 s dès que la suite tourne en parallèle (échecs intermittents **préexistants**, vérifiés sur l'arbre propre avant mes changements).
- Vérifs : Vitest **80 passed** (18 fichiers, +10 vs 6b-i : 8 `layout.test.ts` + 2 cas de page) · `npm run typecheck` 0 erreur · `npm run lint` 0 erreur · `npx playwright test` **9 passed** (+2 `dashboard.spec.ts` ; a11y du dashboard rescané, aucune violation sérieuse) · suite backend **371 passed** (inchangée) · pre-commit ✅ 11 hooks Passed (gitleaks inclus).
- Commit : (à compléter) — `feat: tableau de bord personnalisable (6b-ii-b)`.
- **Non fait** : push (aucun remote GitHub), merge sur `main` (sans feu vert) ; 6c (notifications + export PDF) à suivre.

### Critères de la sous-phase 6b-ii-b — vérité du terrain
| Critère | État |
|---|---|
| Tests frontend | ✅ Vitest **80 passed** (18 fichiers, +10 : 8 `layout.test.ts` + 2 cas de page) |
| Tests e2e | ✅ `npx playwright test` **9 passed** (+2 `dashboard.spec.ts` — déplacement réel, `PUT` puis `DELETE`) |
| Lint/types frontend | ✅ `npm run typecheck` (`tsc -b`) ✅ · `npm run lint` 0 erreur |
| Build | ✅ `npm run build` OK (avertissement « chunk > 500 kB » préexistant) |
| Widgets | ✅ disposition servie par l'API rendue par genre (santé/KPI/objectifs/activité) ; catalogue filtré côté backend |
| Mode édition | ✅ déplacement (poignée) + redimensionnement (coin bas-droit) ; Enregistrer/Annuler/Réinitialiser ; brouillon local tant que rien n'est enregistré |
| Persistance | ✅ enregistrement par mutation (`PUT`) puis relecture ; remise à zéro (`DELETE`) ; disposition par défaut tant qu'aucune ligne n'existe |
| Permissions | ✅ activité jamais servie à un membre (backend) ; aucune garde d'interface redondante (v. `DECISIONS.md`) |
| i18n | ✅ `dashboard.*` FR + EN, aucun texte en dur |
| Backend | ✅ inchangé (suite 371 passed) |
| pre-commit | ✅ 11 hooks Passed (gitleaks inclus) |
| CI frontend | ✅ job `frontend` ajouté à la CI (lint/types/tests/build ; e2e local — Edge) — pas encore exécuté (aucun remote GitHub) |
