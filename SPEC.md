# Cahier des charges — Mirador (nom provisoire)

Document vivant, v0.1. 🔒 = décision validée par le porteur du projet. 💡 = proposition modifiable.

## 1. Vision
- **Problème** : une entreprise jongle entre des dizaines d'outils (compta, facturation, analytics, réseaux sociaux, gestion de projet, mails...).
- **Promesse** : un seul endroit pour « jeter un coup d'œil » et savoir ce qui se passe dans l'entreprise, sans ouvrir 15 onglets.
- **Cible** 🔒 : toute entreprise, tout secteur, toute taille. Le produit reste donc générique ; on adapte via des modèles par secteur (💡 restaurant, agence, e-commerce, artisan), pas via du code spécifique.
- **Principe** 🔒 : tout est dynamique (API, webhooks, MCP). Aucune donnée statique dans l'interface.
- **Objectifs** 🔒 : (1) portfolio et plaisir ; (2) produit publiable et commercialisable.

## 2. Utilisateurs, rôles, permissions
- 1 compte = 1 établissement (MVP) 🔒, rattaché à un SIRET. Les franchises/multi-établissements viendront plus tard : le schéma porte déjà `organization_id` partout.
- Rôles 🔒 : `admin` (le dirigeant) et `member` (collaborateur).
- L'admin invite des collaborateurs par e-mail et choisit, **pour chacun, les modules visibles** : `none` / `view` / `edit` 🔒. 💡 Plus tard : permissions par widget ou connecteur, équipes.
- L'admin peut révoquer un accès à tout moment. Toute modification de permission est journalisée.
- Authentification 🔒 : e-mail + mot de passe, connexion Google, A2F TOTP (💡 obligatoire pour les admins).

## 3. Modules
Chaque module = des KPI canoniques (indépendants de l'outil source), des widgets, des connecteurs.

### MVP 🔒
- **Finance** : CA, dépenses, marge, trésorerie, factures impayées et ancienneté, budget vs réel, top clients/fournisseurs. 💡 Si abonnements : MRR/ARR, churn.
- **Web analytics** : visiteurs, sessions, pages vues, taux d'engagement, durée moyenne, sources de trafic, top pages, conversions, pays/appareils.
- **Réseaux sociaux** : abonnés par réseau et croissance, portée/impressions, taux d'engagement, meilleurs posts, mentions, calendrier de publications.
- **Projets & tâches** : tâches par statut, retards, charge par personne, avancement des projets, jalons à venir, délai moyen de livraison.
- **Identité légale** 🔒 : toutes les informations légales de l'entreprise au même endroit, pré-remplies automatiquement à partir du SIREN.
  - Identité : SIREN, SIRET (siège et établissement du compte), raison sociale, nom commercial/enseigne, forme juridique, date de création, activité (code APE/NAF et libellé), adresse du siège, tranche d'effectif, dirigeants (nom et qualité).
  - Fiscal : n° de TVA intracommunautaire (calculé à partir du SIREN, puis vérifié via VIES).
  - Saisie manuelle (champs absents des registres ouverts ou entreprises « non diffusibles ») : capital social, RCS/greffe, assurances (RC pro...), médiateur de la consommation, convention collective, 💡 coordonnées bancaires pour les factures (chiffrées).
  - Fonctions : bouton « copier » sur chaque champ, bloc « mentions légales » prêt à coller (factures, site web), export PDF, source et date de dernière mise à jour affichées pour chaque donnée, alerte si un registre change (adresse, dirigeant, radiation). Permission dédiée `legal` (💡 consultation pour les membres autorisés, modification réservée à l'admin par défaut) ; données personnelles des dirigeants limitées au strict nécessaire et visibles des admins par défaut.
  - 💡 Plus tard : documents (Kbis, statuts, attestations) avec dates d'expiration et alertes, échéances légales (dépôt des comptes, assemblées).
  - Les registres sont publics mais peuvent avoir du retard ; le Kbis officiel reste un document à demander au greffe/INPI.
- **Vue d'ensemble « Pouls »** 💡 : page d'accueil avec 6-8 KPI clés tous modules confondus, indicateur de santé global, alertes en cours, fil d'activité, objectifs en cours.

### Après le MVP 💡 (ordre de priorité suggéré)
Facturation (devis, factures, relances) → Marketing (e-mailing, campagnes, pubs) → Ventes/CRM (pipeline) → Mails (résumé de boîte, e-mails importants) → Support client (tickets) → RH (effectifs, absences) → E-commerce/stocks → Avis clients.
Note : avant le module Facturation, étudier la réforme française de la facturation électronique (calendrier 2026-2027, à vérifier) : Mirador se brancherait sur des plateformes agréées existantes, sans devenir lui-même plateforme agréée.

## 4. Fonctions transverses 🔒
- **Comparaison de périodes** : vs période précédente, vs même période N-1, plage libre.
- **Objectifs & budgets** : cible sur n'importe quel KPI, progression, alerte en cas de dérive.
- **Recherche globale** : barre de recherche (Ctrl/Cmd+K) sur modules, KPI, projets, tâches, paramètres.
- **Dashboard personnalisable** : widgets ajoutables, déplaçables, redimensionnables ; mise en page sauvegardée par utilisateur ; modèles par défaut.
- **Notifications** : in-app + Web Push (PWA, bureau et mobile) ; règles d'alerte configurables (seuil dépassé, facture impayée, objectif atteint...).
- **Export PDF** : d'un module ou du dashboard, avec comparaison de période. 💡 Rapports planifiés par e-mail plus tard.
- **Chatbot IA** : questions en langage naturel sur les données de l'entreprise. Lecture seule, uniquement les données autorisées pour l'utilisateur courant, via des outils (function calling). Fournisseur LLM interchangeable, quotas par plan.
- **Paramétrage** : onglet où l'admin connecte ses outils thématique par thématique (OAuth, clé API, webhook), voit l'état de chaque connexion, peut la déconnecter.
- **i18n** : français (défaut) et anglais, architecture prête pour d'autres langues ; dates, nombres et devises localisés.

## 5. Architecture technique

### 5.1 Flux de données 💡
```
[Outils tiers] --API / webhooks / MCP--> [Connecteurs] --> [Normalisation en métriques canoniques]
                                                                      |
[Planificateur 5 min] ---------------------------------------> [PostgreSQL] <--> [API FastAPI] <--> [Frontend React]
                                                                                        |
                                                                              [SSE temps réel, plus tard]
```

### 5.2 Stack et justifications
- **Backend** : FastAPI + Pydantic v2 + SQLAlchemy 2 async + Alembic. Performant, typé, OpenAPI automatique (→ client TypeScript généré), très bien maintenu 🔒 (préférence FastAPI/Python).
- **Base** : PostgreSQL 🔒. JSONB pour les dimensions des métriques, Row-Level Security pour le multi-tenant, partitionnement mensuel des snapshots si le volume l'exige. Pas de base dédiée séries temporelles au MVP.
- **Frontend** 💡 : SPA React + TypeScript + Vite plutôt que Next.js. Le backend est déjà FastAPI et un dashboard derrière login n'a pas besoin de SSR ; on évite ainsi de dupliquer la logique serveur dans deux endroits. Librairies : React Router, TanStack Query, Tailwind, shadcn/ui, Recharts, i18next, Motion.
- **Tâches planifiées** 💡 : service `worker` séparé, derrière une interface `JobScheduler`, pour pouvoir passer plus tard à une vraie file (ARQ ou Celery + Redis) sans toucher au métier.
- **Temps réel** : MVP = polling (TanStack Query, toutes les 5 min). Version finale = webhooks entrants + SSE vers le navigateur (plus simple qu'un WebSocket pour un flux à sens unique) 🔒 « temps réel si ça ne ralentit pas ».
- **Webhooks entrants** : `/webhooks/{provider}` avec vérification de signature, idempotence, traitement asynchrone.
- **MCP** : un connecteur peut s'appuyer sur un serveur MCP. Phase ultérieure, derrière l'interface `Connector`.
- **API** : REST versionnée `/api/v1`, erreurs normalisées (RFC 9457), pagination, OpenAPI.

### 5.3 Modèle de données (haut niveau)
`organizations` (rattachée à un SIRET) · `users` · `memberships` (rôle) · `module_permissions` (membership, module, niveau) · `invitations` · `connections` (provider, catégorie, statut, identifiants chiffrés, dernière synchro) · `metric_snapshots` (organization_id, clé `module.metric`, période, valeur, dimensions JSONB, capturé le) · `goals` · `alert_rules` · `notifications` · `dashboard_layouts` · `audit_logs` · `legal_profiles` (champs légaux, source et date de synchro par champ) · `legal_identifiers` (pays, schéma, valeur, source, vérifié le) · `legal_documents` (plus tard : type, fichier chiffré, échéance) · `subscriptions` (identifiants Stripe).
Toutes les tables métier portent `organization_id`.

### 5.4 Connecteurs (cœur du produit)
- Interface `Connector` : `provider`, `category`, `auth_type`, `connect()`, `sync(since)`, `handle_webhook(payload)`, `disconnect()`, `healthcheck()`.
- **Métriques canoniques** : clé `module.metric` (ex. `finance.revenue`), unité, période, valeur, dimensions. Un connecteur réel et un mock produisent **exactement** le même format : basculer de l'un à l'autre ne change rien au reste de l'application.
- **MockConnector** (un par catégorie) 🔒 : génère une entreprise fictive cohérente et réaliste (saisonnalité, tendances, quelques anomalies), déterministe via un seed. Sert au MVP, aux tests et à la démo.
- Premiers connecteurs réels 💡 : Stripe (finance), Google Analytics 4 (web), un réseau social, un outil de tâches.
- **Règles de validation** : SIREN/SIRET contrôlés par l'algorithme de Luhn (des exceptions existent, par exemple les établissements de La Poste : à vérifier dans la doc) ; clé du n° de TVA français = (12 + 3 × (SIREN mod 97)) mod 97, donc `FR` + clé + SIREN. Une entreprise peut avoir un SIREN valide sans n° de TVA : ne jamais l'exiger. Pays : France d'abord ; autres pays plus tard via `legal_identifiers`, saisie manuelle + VIES en attendant.
- **Source et priorité** : chaque champ légal mémorise sa source (`registry` ou `manual`) et sa date de synchro ; la saisie manuelle prime, et un écart avec le registre déclenche une alerte plutôt qu'un écrasement.
- **Registres officiels (module Identité légale)** : service `LegalRegistry`, **connecteur réel dès le MVP 🔒** (aucun identifiant à fournir pour la source principale). Source principale : API Recherche d'entreprises (gratuite, sans clé, agrège Sirene, RNE et INPI ; limite d'environ 7 requêtes/seconde à respecter, avec cache, timeouts et backoff). Repli : API Sirene de l'INSEE (clé requise, environ 30 requêtes/minute). TVA : calcul depuis le SIREN + vérification VIES. Appels toujours faits par le backend, jamais par le navigateur. Schéma générique `legal_identifiers(pays, schéma, valeur, source, vérifié le)` pour ouvrir plus tard à d'autres pays. Compléments possibles : BODACC (annonces légales). Les limites de débit citées sont des ordres de grandeur à revérifier dans les documentations officielles : ne rien deviner.

## 6. Sécurité & RGPD
- Mesures techniques : voir AGENTS.md §5. En plus : A2F, journal d'audit, chiffrement des tokens tiers (AES-GCM, clé hors base, rotation possible), sauvegardes chiffrées, hébergement dans l'UE.
- Côté produit : registre des traitements, mentions légales, CGU/CGV, politique de confidentialité et cookies, export et suppression des données, DPA pour les clients B2B.
- Données de l'entreprise : pour un entrepreneur individuel, nom et adresse peuvent être des données personnelles ; certaines entreprises ont un statut de diffusion restreint (informations limitées dans les API publiques, à vérifier dans leur documentation). Prévoir la saisie manuelle et ne jamais rediffuser ces données.
- ⚠️ Avant toute commercialisation, faire valider les aspects juridiques (RGPD, CGU/CGV, TVA) par un professionnel. Ce document n'est pas un avis juridique.

## 7. Design & UX 🔒
- Moderne, coins arrondis, mode clair/sombre, **menu latéral gauche**, personnalisable. Inspirations : Notion, Stripe, Claude, Qrood.fr.
- Effets « wow » : compteurs animés, transitions de pages, graphiques animés, skeleton loaders, micro-interactions. Sobres et performants ; `prefers-reduced-motion` respecté.
- Desktop first. L'app mobile native viendra plus tard (le MVP reste responsive de base).
- États vides, chargement et erreur soignés sur chaque widget. Accessibilité WCAG AA.
- Design tokens (couleurs, rayons, espacements) en variables CSS pour que light/dark et le futur branding soient triviaux.

## 8. Plans tarifaires 💡 (v2, après étude de marché du 3 octobre 2026)

### 8.1 Repères du marché
Prix publics relevés sur des comparateurs et des sites d'éditeurs, en USD par mois, facturation annuelle sauf mention. Les sources se contredisent parfois : ce sont des fourchettes, à revérifier sur les pages officielles avant de fixer les prix.

| Outil | Positionnement | Prix repères |
|---|---|---|
| Power BI Pro | BI généraliste, par utilisateur | 14 $ / utilisateur |
| Zoho Analytics | BI, par compte | 30 $ (2 util.) · 60 $ (5) · 145 $ (15) · 575 $ (Enterprise) |
| Geckoboard | KPI en direct | entrée ≈ 44-119 $ selon la source ; palier haut ≈ 400-615 $ |
| Databox | KPI marketing/ops, par source de données | gratuit (3 sources) ; payant ≈ 47-159 $ en entrée, ≈ 399 $ (Growth), jusqu'à ≈ 799 $ ; source en plus ≈ 5,6 $ ; marque blanche ≈ 80 $ |
| Agicap | Trésorerie (France/Europe) | sur devis, segment plutôt haut |

Constats :
1. Les 19 € / 49 € de la v1 étaient sous l'entrée de presque tous les concurrents.
2. Un produit tout-en-un (finance + web + social + projets + légal + chatbot) justifie plus qu'un simple tableau de KPI.
3. Mais les concurrents ont des dizaines d'intégrations (Geckoboard : 90+), le MVP en aura 3 ou 4 : le prix de liste doit monter avec le catalogue de connecteurs.
4. Standards du marché : −20 % en annuel, essai de 14 jours, paliers par sources ou utilisateurs, marque blanche en option.

Limite : aucune donnée sur le consentement à payer des TPE/PME françaises. À valider par 8-10 entretiens avec des dirigeants à partir de la démo.

### 8.2 Grille proposée (HT, par mois, facturation mensuelle)
| | Essentiel | Pro ⭐ | Business | Entreprise |
|---|---|---|---|---|
| Prix | 39 € | 99 € | 249 € | dès ~590 €, sur devis |
| Utilisateurs | 3 | 10 | 30 | Illimité |
| Connecteurs | 3 | 8 | Illimité | Illimité |
| Rafraîchissement | 30 min | 15 min | 5 min → temps réel | Temps réel |
| Historique | 12 mois | 24 mois | 36 mois | Personnalisé |
| Fiche légale | Oui | + alertes d'échéance | + veille BODACC | Oui |
| Export PDF, objectifs | Non | Oui | Oui | Oui |
| Chatbot IA | Non | Quota | Quota étendu | Sur mesure |
| Permissions par module | Basiques | Complètes | + journal d'audit exportable | + SSO |
| Marque blanche | Non | Option | Légère incluse | Oui |
| Support | E-mail | E-mail | Prioritaire | SLA |

Options et règles :
- −20 % en facturation annuelle ; essai de 14 jours du plan Business, sans carte.
- Utilisateur en plus ≈ 5 €/mois ; connecteur en plus ≈ 6 €/mois ; marque blanche ≈ 79 €/mois sur Pro.
- Offre « Fondateurs » : −30 % à vie pour les ~20 premiers clients. Les prix de liste montent quand le catalogue grandit, sans toucher aux fondateurs.
- Pas de plan gratuit permanent au lancement (support, abus ; certains concurrents en ont supprimé) : démo publique + essai de 14 jours. À reconsidérer plus tard comme canal d'acquisition.
- Quotas du chatbot à calibrer sur le coût réel du LLM ; recalculer la marge (LLM, hébergement, support) avant de figer les prix.
- Prix HT (cible B2B). TVA : Stripe Tax ou équivalent, à valider.

### 8.3 Stripe
Products/Prices, Checkout, Customer Portal, webhooks (`checkout.session.completed`, `invoice.paid`, `customer.subscription.updated`, `customer.subscription.deleted`). Les droits de chaque plan vivent dans une table d'entitlements côté code, jamais éparpillés dans l'UI.

## 9. Mode démo 🔒
- But : montrer le produit aux dirigeants intéressés, et laisser des visiteurs essayer sans inscription.
- Entreprise fictive complète alimentée par les MockConnectors, avec plusieurs scénarios sectoriels (💡 restaurant, agence, e-commerce).
- Bac à sable : le visiteur peut jouer (changer les périodes, déplacer des widgets, chatbot plafonné) mais rien n'est conservé ; remise à zéro automatique.
- Accès : `/demo` public + 💡 liens à durée limitée `/demo/<token>` générés pour un prospect, avec choix du secteur.
- Organisation marquée `is_demo`, isolée des vraies données, rate limiting renforcé, bandeau « Démo » avec appel à l'inscription. Les identifiants légaux de la société fictive sont signalés comme fictifs et la vérification auprès des registres est désactivée en démo.

## 10. Déploiement & hébergement
**Principe** : en production, la base contient les données financières de clients. La base est l'actif à ne jamais perdre ; le calcul, lui, doit être jetable et reconstruisible en minutes. Pour un développeur seul (2-3 h par soir), le temps passé à administrer des serveurs n'est pas passé sur le produit.

### Recommandation 💡 : PaaS managé français
Scalingo ou Clever Cloud : deux PaaS français, déploiement par Git, PostgreSQL managé, hébergement en France/UE.
- **Pourquoi** : correctifs système, sauvegardes, TLS et montée en charge pris en charge par l'hébergeur ; argument commercial « hébergé en France » et RGPD facilité ; une seule chaîne de déploiement pour la démo publique et pour la production.
- **Contreparties** : coût par ressource plus élevé qu'un VPS (faible face à un abonnement à 99 €) ; dépendance à la plateforme, atténuée par Docker + PostgreSQL standard + API S3.
- **Repères relevés** (comparateurs et avis tiers, à vérifier sur les sites officiels) : Scalingo, PaaS « façon Heroku », PostgreSQL managé dès ≈ 7,20 €/mois, certifications annoncées (HDS ; un avis d'utilisateur cite un datacenter SecNumCloud) ; Clever Cloud, PaaS plus généraliste, tarification à l'usage, applications Docker et nombreux services managés.
- **Comparatif court au début de la phase 11**, consigné dans `docs/adr/hebergement.md`, selon cette checklist : images Docker ou buildpack Python ; processus `worker` et tâches planifiées ; **connexions longues (SSE)** et timeouts du routeur ; PostgreSQL managé avec sauvegardes, restauration à un instant donné et durée de rétention ; région France/UE ; prix au volume prévu (api, worker, base, stockage) ; export des sauvegardes ; logs et métriques ; certifications et contrat de sous-traitance (DPA).

### Plan B : IaaS 💡
Si les contraintes ou les coûts l'exigent : instance/VPS chez OVHcloud ou Scaleway (Hetzner, en Allemagne, reste une alternative UE, tarifs non comparés ici) + PostgreSQL managé + stockage objet S3, derrière Caddy. Ordre de grandeur relevé sur un comparateur : PostgreSQL managé 2 vCPU / 4 Go ≈ 37-51 $/mois (données potentiellement anciennes). Plus de contrôle et souvent moins cher, mais tu administres le système (mises à jour, durcissement, supervision).

### À éviter
Un VPS unique qui héberge aussi la base, pour de vrais clients : acceptable en dev, pour une démo sans donnée réelle ou un staging, pas pour les données financières de clients payants. Kubernetes et multi-régions : trop tôt, à reconsidérer si la charge ou des exigences clients (SLA) le justifient.

### Quel que soit l'hébergeur
- Dev : Docker Compose en local.
- Secrets injectés au déploiement, jamais dans Git ; configuration d'infrastructure de production dans un **dépôt privé séparé** (le dépôt du produit est public).
- Supervision : suivi d'erreurs, logs, uptime avec alertes, page de statut.
- Une restauration de sauvegarde est testée à date fixe : une sauvegarde jamais restaurée n'est pas une sauvegarde.

### CI/CD
GitHub Actions : lint, types, tests, détection de secrets, audit des dépendances, build des images, déploiement avec rollback.

## 11. Hors périmètre du MVP
App mobile native, multi-établissements/franchises, SSO entreprise, marketplace de connecteurs, marque blanche, registres légaux hors France.

## 12. Dépôt public & licence 🔒 repo public · 💡 licence
- Le dépôt GitHub est public (portfolio) et le produit sera peut-être commercialisé : la licence doit permettre les deux.
- **Recommandation** : FSL-1.0-Apache-2.0 (Functional Source License). Le code est lisible, modifiable et utilisable pour tout usage sauf un usage concurrent (produit ou service commercial qui concurrence Mirador) ; chaque version passe automatiquement en Apache 2.0 deux ans après sa publication. Ce n'est pas une licence « open source » au sens OSI pendant ces deux ans.
- **Alternatives** : (1) aucune licence, tous droits réservés : protection maximale mais message flou pour un portfolio ; (2) AGPLv3 : vrai open source, mais un concurrent peut héberger ton produit tant qu'il publie ses modifications, et une double licence n'est possible que si tu détiens tous les droits ; (3) MIT/Apache : n'importe qui peut revendre le produit, incompatible avec la commercialisation.
- Contributions externes : fermées au départ (`CONTRIBUTING.md` l'explique) ; si elles ouvrent plus tard, prévoir un CLA ou un DCO.
- ⚠️ Faire valider le choix par un juriste avant commercialisation (notamment la définition d'usage concurrent). Vérifier les licences des dépendances (CI : pip-licenses, license-checker).
- **Hygiène d'un dépôt public** : jamais de secret (gitleaks en pre-commit et en CI, GitHub secret scanning avec push protection), pas de données clients réelles ni de vrais identifiants dans les fixtures, `SECURITY.md` (signalement de vulnérabilités), Dependabot, branche `main` protégée. L'historique Git est public pour toujours : un secret commité est compromis, même supprimé ensuite.
- Le README sert de vitrine : captures ou GIF, lien vers la démo, stack, architecture, choix techniques.
- **À confirmer avant le premier push public** : une version publiée sous une licence reste sous cette licence, le choix doit donc être fait avant de publier.
- Marque : le nom et le logo ne sont pas couverts par la licence (politique de marque dans le README). Vérifier nom de domaine et INPI avant d'investir dans le branding.
