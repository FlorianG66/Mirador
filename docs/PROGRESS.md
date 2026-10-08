# Progression

> Fichier de reprise : si tu perds le fil, lis `AGENTS.md`, ce fichier, puis la phase en cours dans `ROADMAP.md`.

## État

- **Phase en cours** : 2 — Auth, organisations, permissions. Découpage en sous-phases :
  2a modèle + RLS + repositories (**livrée et commitée**), 2b inscription/connexion/sessions/CSRF/rate-limit (**livrée et commitée**),
  2c A2F TOTP + codes de secours + mot de passe oublié (**livrée et commitée**), 2d invitations/permissions/révocation/audit (**livrée et commitée**), 2e Google OIDC.
- **Branche** : `phase-2-auth-organisations` (créée depuis `phase-1-backend-socle`).
- **Prochaine action** : sous-phase 2e — connexion Google (OIDC).
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
