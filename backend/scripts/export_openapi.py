"""Exporte le schéma OpenAPI de l'application vers le frontend.

Le client TypeScript est généré à partir de ce snapshot (`npm run generate:api`
dans `frontend/`). On l'écrit sur disque plutôt que de servir le schéma en
production : la génération n'a pas besoin d'un backend lancé ni d'une base.

Usage, depuis `backend/` : ``python -m scripts.export_openapi``
"""

import json
from pathlib import Path

from app.main import create_app

# Racine du dépôt puis frontend/openapi/schema.json (parents[2] = racine).
REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "frontend" / "openapi" / "schema.json"


def main() -> None:
    """Construit l'app (sans connexion base) et écrit le schéma JSON."""
    app = create_app()
    schema = app.openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
    print(f"Schéma OpenAPI écrit : {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
