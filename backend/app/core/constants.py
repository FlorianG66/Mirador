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
