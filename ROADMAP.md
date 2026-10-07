# Roadmap — Mirador (nom provisoire)

Une phase = une branche `phase-N-nom`, et chaque phase finit par : tests verts → doc → commit/push (voir AGENTS.md §3).
Si une phase est trop grosse pour une session, la découper en Na / Nb.

**Jalon A — Démo / portfolio** : phases 0 à 8 (données fictives, tout fonctionne, démo présentable).
**Jalon B — Commercialisable** : phases 9 à 11 (vrais connecteurs, paiement, production).

---

## Phase 0 — Fondations du repo
**Réf. SPEC** : §10, §12
- Monorepo : `backend/`, `frontend/`, `docs/`, `infra/`, `.github/workflows/`.
- Fichiers racine : `README.md` (squelette), `.gitignore`, `.editorconfig`, `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/PROGRESS.md`. `LICENSE` (FSL-1.0-Apache-2.0, voir SPEC §12 ; me faire confirmer avant le premier push public), `SECURITY.md`.
- Docker Compose avec PostgreSQL (volume persistant) et `.env.example`.
- pre-commit (ruff, eslint, gitleaks) et CI GitHub Actions (squelette, avec gitleaks) ; Dependabot. Dépôt public : aucun secret ne doit jamais être commité (SPEC §12) ; secret scanning + push protection GitHub, protection de la branche `main`, `CONTRIBUTING.md` (contributions fermées au départ).
**Critères** : `docker compose up` démarre la base ; la CI s'exécute et passe ; gitleaks ne détecte rien.

## Phase 1 — Backend socle
**Réf. SPEC** : §5.2
- Projet FastAPI structuré (`routers`, `services`, `repositories`, `models`, `schemas`, `core`).
- Config via pydantic-settings, logging structuré, erreurs normalisées (RFC 9457), `GET /api/v1/health`.
- SQLAlchemy 2 async + Alembic, première migration, base de test isolée.
**Tests** : pytest sur health, connexion DB, gestion d'erreurs.

## Phase 2 — Auth, organisations, permissions
**Réf. SPEC** : §2, §6 ; AGENTS.md §5
- Tables : organizations, users, memberships, module_permissions, invitations, audit_logs.
- Inscription (crée l'organisation + l'admin ; champ SIREN optionnel, validé par la clé de Luhn, le pré-remplissage automatique arrive en 5e), connexion e-mail/mot de passe (Argon2id), Google OIDC, A2F TOTP + codes de secours, sessions par cookies avec rotation des refresh tokens, mot de passe oublié.
- Invitation d'un collaborateur avec choix des modules visibles ; révocation d'accès.
- Isolation tenant : dépendance `current_tenant` + RLS PostgreSQL. Rate limiting, en-têtes de sécurité, CSRF.
**Tests** : parcours auth complets ; un tenant ne lit jamais les données d'un autre ; un `member` sans accès à un module reçoit 403 ; rate limit ; journal d'audit alimenté.

## Phase 3 — Frontend socle & design system
**Réf. SPEC** : §7, §4 (i18n)
- Vite + React + TypeScript strict, routing, layout avec **menu latéral gauche**.
- Design tokens, thème clair/sombre, i18n FR/EN, composants de base (carte, carte KPI, wrapper de graphique, skeletons, états vides/erreur).
- Client API généré depuis l'OpenAPI ; gardes de routes selon permissions.
- Pages : connexion, inscription, A2F, Paramètres › Équipe (invitations, permissions par module).
**Tests** : Vitest sur composants clés, e2e Playwright du login, build OK, vérification a11y de base.

## Phase 4 — Connecteurs & données fictives
**Réf. SPEC** : §5.3, §5.4
- Interface `Connector`, registre de connecteurs, métriques canoniques.
- `MockConnector` par catégorie (finance, web, social, projets/tâches) : déterministe via seed, réaliste (saisonnalité, tendances, anomalies).
- Table `metric_snapshots`, service worker + `JobScheduler` : synchro toutes les 5 min (configurable).
- Endpoint générique de lecture des métriques, filtré par tenant et permissions.
**Tests** : déterminisme du seed, format canonique respecté, planificateur, isolation tenant.

## Phase 5 — Modules MVP (une sous-phase par module)
**Réf. SPEC** : §3
Pour chaque module : endpoints métier, page dédiée, widgets, états chargement/vide/erreur, polling 5 min, animations « wow » sobres.
- **5a Finance** · **5b Web analytics** · **5c Réseaux sociaux** · **5d Projets & tâches**
- **5e Identité légale** (SPEC §3, §5.4) : service `LegalRegistry` (API Recherche d'entreprises, repli API Sirene INSEE, vérification de TVA via VIES) avec cache, timeouts et gestion des limites de débit ; validation SIREN/SIRET (Luhn) et calcul du n° de TVA intracommunautaire ; inscription pré-remplie à partir du SIREN ; fiche légale (copie en un clic, bloc « mentions légales », export PDF, source et date de chaque donnée) ; saisie manuelle des champs absents et des entreprises non diffusibles ; détection de changements avec alerte ; permission dédiée `legal`.
- **5f Vue d'ensemble « Pouls »** : KPI clés, santé globale, alertes, fil d'activité.
**Tests** : API (par module et par permission) et UI (rendu, états, i18n FR/EN). Pour 5e : algorithmes de validation (cas limites), réponses des registres simulées (jamais d'appel réel en CI), entreprise non diffusible, changement détecté → alerte, permission `legal`.

## Phase 6 — Fonctions transverses
**Réf. SPEC** : §4
- **6a** Comparaison de périodes + objectifs/budgets avec alertes de dérive.
- **6b** Recherche globale (Ctrl/Cmd+K) + dashboard personnalisable (drag & drop, redimensionnement, layouts sauvegardés).
- **6c** Notifications (in-app + Web Push, règles d'alerte) + export PDF (choix de la technique documenté dans DECISIONS, privilégier la simplicité).
**Tests** : calculs de comparaison, déclenchement des alertes, persistance des layouts, génération PDF.

## Phase 7 — Mode démo
**Réf. SPEC** : §9
- Organisation `is_demo` isolée (identifiants légaux fictifs signalés comme tels, aucun appel aux registres), scénarios sectoriels, `/demo` public, liens `/demo/<token>` à durée limitée, remise à zéro automatique, bandeau « Démo », rate limiting renforcé.
**Tests** : aucune fuite entre démo et vrais tenants, expiration des liens, reset.

## Phase 8 — Chatbot IA
**Réf. SPEC** : §4
- Interface LLM interchangeable (fournisseur configurable), outils en lecture seule branchés sur les métriques, respect strict des permissions de l'utilisateur, quotas, historique de conversation.
**Tests** : le chatbot ne répond jamais avec des données d'un module non autorisé ; quotas ; fournisseur mocké dans la CI.

---
*Fin du jalon A : démo présentable.*

## Phase 9 — Paramétrage & premiers connecteurs réels
**Réf. SPEC** : §4 (Paramétrage), §5.2 (webhooks, SSE, MCP), §5.4
- Onglet Paramètres › Connexions : connecter/déconnecter par thématique, état de santé.
- Stockage chiffré des identifiants tiers. Webhooks entrants signés et idempotents.
- 2 à 3 connecteurs réels (💡 Stripe, Google Analytics 4, un outil de tâches).
- SSE pour pousser les mises à jour vers le navigateur ; mesurer l'impact sur les performances et vérifier la gestion des connexions longues chez l'hébergeur (SPEC §10).
**Tests** : connecteurs contre des réponses simulées (jamais de vraies clés dans la CI), signature des webhooks, chiffrement/déchiffrement.

## Phase 10 — Plans & paiement Stripe
**Réf. SPEC** : §8
- Plans (valeurs de SPEC §8, stockées en configuration et non en dur), table d'entitlements, Checkout, Customer Portal, webhooks Stripe, essai gratuit, gestion des dépassements de quotas.
**Tests** : droits par plan, webhooks Stripe rejoués, passage de plan montant/descendant.

## Phase 11 — Production
**Réf. SPEC** : §6, §10
- Pages légales, export/suppression RGPD, durcissement sécurité (revue ASVS), sauvegardes, supervision, choix de l'hébergeur par un comparatif court selon la checklist de SPEC §10 (Scalingo, Clever Cloud, ou plan B IaaS) consigné dans `docs/adr/hebergement.md`, puis déploiement automatisé avec rollback, dépôt privé d'infra, test de restauration d'une sauvegarde, nom de domaine, e-mails transactionnels.
**Tests** : scénario de bout en bout en préproduction, restauration d'une sauvegarde, audit des dépendances.
