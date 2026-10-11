"""Repository des identifiants légaux génériques (SPEC §5.3). Accès aux données uniquement."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_identifier import LegalIdentifier


async def list_for_organization(
    session: AsyncSession, organization_id: uuid.UUID
) -> list[LegalIdentifier]:
    """Tous les identifiants de l'organisation, ordonnés (stable pour l'UI)."""
    statement = (
        select(LegalIdentifier)
        .where(LegalIdentifier.organization_id == organization_id)
        .order_by(LegalIdentifier.pays, LegalIdentifier.schema)
    )
    result = await session.execute(statement)
    return list(result.scalars())


async def upsert(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    pays: str,
    schema: str,
    valeur: str,
    source: str,
    verified_at: datetime | None = None,
) -> None:
    """Crée ou remplace l'identifiant `(pays, schéma)` de l'organisation (idempotent)."""
    statement = pg_insert(LegalIdentifier).values(
        organization_id=organization_id,
        pays=pays,
        schema=schema,
        valeur=valeur,
        source=source,
        verified_at=verified_at,
    )
    statement = statement.on_conflict_do_update(
        constraint="legal_identifiers_org_pays_schema",
        set_={"valeur": statement.excluded.valeur, "source": statement.excluded.source},
    )
    await session.execute(statement)
