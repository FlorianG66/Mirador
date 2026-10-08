"""Constantes applicatives.

Le nom du projet est provisoire : il vit ici et nulle part ailleurs (AGENTS.md §1).
"""

PROJECT_NAME = "Mirador"
API_SERVICE = "mirador-api"
# Doit suivre la version de backend/pyproject.toml (même numéro de release).
API_VERSION = "0.1.0"
API_PREFIX = "/api/v1"

# Cookies d'authentification (phase 2b) : noms imposés au frontend comme au backend.
ACCESS_COOKIE = "mirador_access"
REFRESH_COOKIE = "mirador_refresh"
CSRF_COOKIE = "mirador_csrf"
CSRF_HEADER = "x-csrf-token"

# A2F et récupération de compte (phase 2c).
TWO_FACTOR_COOKIE = "mirador_2fa"
TWO_FACTOR_CHALLENGE_TTL_SECONDS = 5 * 60
PASSWORD_RESET_TOKEN_TTL_SECONDS = 30 * 60
BACKUP_CODE_COUNT = 10

# Invitation d'un collaborateur (phase 2d) : le lien expire au bout d'une semaine.
INVITATION_TTL_SECONDS = 7 * 24 * 3600
# Nombre maximal de journaux d'audit renvoyés par requête.
AUDIT_LOGS_LIMIT = 100

# Connexion Google (phase 2e) : cookie d'état du parcours OIDC, usage unique.
OAUTH_STATE_COOKIE = "mirador_oauth_state"
OAUTH_STATE_TTL_SECONDS = 10 * 60
