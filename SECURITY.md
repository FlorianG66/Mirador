# Sécurité

## Signaler une vulnérabilité

Merci de **ne pas** ouvrir une issue publique pour une vulnérabilité.

Envie un e-mail ou utilise le formulaire de signalement privé GitHub (Security tab → Report a vulnerability) en décrivant :
- le problème constaté et les étapes pour le reproduire ;
- l'impact potentiel ;
- une éventuelle correction suggérée.

Tu reçois un accusé de réception sous 72 h ; correction prioritaire selon la sévérité.

## Portée

Ce dépôt est public (portfolio) : aucun secret, aucune donnée client réelle ni identifiant de production ne doit y figurer. Si tu trouves un secret commité, signale-le : il sera révoqué, pas seulement supprimé.

## Verrous de sécurité du projet

- Détection de secrets : gitleaks en pre-commit et en CI, secret scanning + push protection GitHub.
- Mots de passe : Argon2id. Sessions par cookies httpOnly + Secure + SameSite, rotation des refresh tokens.
- Multi-tenant : filtrage par `organization_id` sur chaque table métier + PostgreSQL Row-Level Security.
- Référence : OWASP ASVS niveau 2 ; `pip-audit` et `npm audit` en CI.
