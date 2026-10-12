"""Service de la fiche légale (SPEC §3, §5.4) : lecteur, mise à jour, rafraîchissement.

Règles portées ici (aucune logique dans le routeur) :

- **La saisie manuelle prime.** Le rafraîchissement depuis le registre n'écrase
  jamais un champ marqué `manual` : un écart devient une alerte d'audit
  (`legal.profile.diverged`), pas un écrasement.
- **La provenance est par champ** : `field_sources` mémorise `registry` ou `manual`
  et la date de synchronisation, pour que l'UI montre d'où vient chaque valeur.
- **Le numéro de TVA est calculé** depuis un SIREN valide (`computed`), jamais saisi.
- **Les dirigeants sont masqués hors admin** (données personnelles, SPEC §3) : le
  routeur décide de les inclure selon le rôle.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.siren import french_vat_number, is_valid_siren
from app.models.legal_identifier import IDENTIFIER_SCHEMA_VAT, LegalIdentifier
from app.models.legal_profile import LEGAL_PROFILE_TEXT_FIELDS, LegalProfile
from app.repositories import legal_identifiers as legal_identifiers_repository
from app.repositories import legal_profiles as legal_profiles_repository
from app.schemas.legal import (
    FieldSourceOut,
    LegalDirectorOut,
    LegalIdentifierOut,
    LegalProfileOut,
    LegalProfileUpdate,
)
from app.services import audit as audit_service
from app.services.errors import ServiceProblem
from app.services.legal_registry import LegalRegistry, LegalRegistryError

VAT_COUNTRY = "FR"

# Champs de la fiche alimentés par le registre : nom API Recherche d'entreprises → colonne.
_REGISTRY_TEXT_FIELDS: dict[str, str] = {
    "siret_siege": "siret_siege",
    "raison_sociale": "raison_sociale",
    "nom_commercial": "nom_commercial",
    "forme_juridique": "forme_juridique",
    "code_naf": "code_naf",
    "libelle_naf": "libelle_naf",
    "adresse_siege": "adresse",
    "tranche_effectif": "tranche_effectif",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _stamp(source: str, at: datetime) -> dict[str, str]:
    """Entrée de `field_sources` : provenance et date de synchronisation (ISO 8601)."""
    return {"source": source, "synced_at": at.isoformat()}


async def _load_or_create(session: AsyncSession, organization_id: uuid.UUID) -> LegalProfile:
    """Fiche de l'organisation, créée à la volée si elle n'existe pas encore."""
    profile = await legal_profiles_repository.get_by_organization(session, organization_id)
    if profile is None:
        profile = legal_profiles_repository.create(session, organization_id)
    return profile


async def get_profile(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    organization_siren: str | None,
    include_directors: bool,
) -> LegalProfileOut:
    """Fiche de l'organisation ; vide mais non nulle tant qu'aucun champ n'est saisi."""
    profile = await legal_profiles_repository.get_by_organization(session, organization_id)
    identifiers = await legal_identifiers_repository.list_for_organization(session, organization_id)
    siren = profile.siren if profile is not None else organization_siren
    if profile is None:
        return _to_out(
            siren=siren,
            values={},
            field_sources={},
            dirigeants=[],
            identifiers=identifiers,
            updated_at=None,
            include_directors=include_directors,
        )
    return _to_out(
        siren=siren,
        values={field: getattr(profile, field) for field in LEGAL_PROFILE_TEXT_FIELDS},
        field_sources=dict(profile.field_sources or {}),
        dirigeants=[LegalDirectorOut(**item) for item in (profile.dirigeants or [])],
        date_creation=profile.date_creation,
        identifiers=identifiers,
        updated_at=profile.updated_at,
        include_directors=include_directors,
    )


async def update_profile(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    organization_siren: str | None,
    actor_user_id: uuid.UUID,
    payload: LegalProfileUpdate,
) -> LegalProfileOut:
    """Écrit les champs fournis en source `manual` (les autres restent inchangés).

    Seuls les champs explicitement présents dans le corps sont touchés : un champ
    omis garde sa valeur et sa provenance. Un SIREN valide (re)calcule la TVA.
    """
    profile = await _load_or_create(session, organization_id)
    provided = payload.model_fields_set
    at = _now()
    sources = dict(profile.field_sources or {})
    changed: list[str] = []

    for field in (*LEGAL_PROFILE_TEXT_FIELDS, "date_creation"):
        value = getattr(payload, field)
        if field in provided and value is not None:
            setattr(profile, field, value)
            sources[field] = _stamp("manual", at)
            changed.append(field)

    if "siren" in provided and payload.siren is not None:
        profile.siren = payload.siren
        sources["siren"] = _stamp("manual", at)
        changed.append("siren")

    # Une liste fournie (même vide) remplace les dirigeants en source manuelle.
    if payload.dirigeants is not None:
        profile.dirigeants = [director.model_dump() for director in payload.dirigeants]
        sources["dirigeants"] = _stamp("manual", at)
        changed.append("dirigeants")

    profile.field_sources = sources
    profile.updated_at = at

    siren = profile.siren or organization_siren
    if siren is not None and is_valid_siren(siren):
        await legal_identifiers_repository.upsert(
            session,
            organization_id=organization_id,
            pays=VAT_COUNTRY,
            schema=IDENTIFIER_SCHEMA_VAT,
            valeur=french_vat_number(siren),
            source="computed",
        )

    await session.flush()
    await audit_service.record(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="legal.profile.updated",
        resource_type="legal_profile",
        resource_id=str(profile.id),
        payload={"fields": changed},
    )
    return await _out_from_row(
        session,
        profile=profile,
        organization_siren=siren,
        include_directors=True,
    )


async def refresh_profile(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    organization_siren: str | None,
    actor_user_id: uuid.UUID,
    registry: LegalRegistry,
) -> LegalProfileOut:
    """Recharge la fiche depuis le registre, sans écraser la saisie manuelle.

    En cas d'écart entre une valeur manuelle et le registre, la valeur manuelle est
    conservée et l'écart est journalisé (`legal.profile.diverged`). L'appel au
    registre peut échouer : le service traduit alors en `ServiceProblem` (502/404).
    """
    profile = await _load_or_create(session, organization_id)
    siren = profile.siren or organization_siren
    if siren is None:
        raise ServiceProblem(400, "Renseignez un SIREN avant de rafraîchir la fiche.")
    try:
        company = await registry.fetch_by_siren(siren)
    except LegalRegistryError as exc:
        raise ServiceProblem(502, "Registre d'identité légale injoignable.") from exc
    if company is None:
        raise ServiceProblem(404, "Aucune entreprise trouvée pour ce SIREN.")

    at = _now()
    sources = dict(profile.field_sources or {})
    changed: list[str] = []
    diverged: list[dict[str, Any]] = []

    profile.siren = company.siren
    sources["siren"] = _stamp("registry", at)

    for field, attribute in _REGISTRY_TEXT_FIELDS.items():
        new_value = getattr(company, attribute)
        if new_value is None:
            continue
        _merge_registry_value(
            profile,
            sources,
            field=field,
            new_value=new_value,
            at=at,
            changed=changed,
            diverged=diverged,
        )

    if company.date_creation is not None:
        _merge_registry_value(
            profile,
            sources,
            field="date_creation",
            new_value=company.date_creation,
            at=at,
            changed=changed,
            diverged=diverged,
        )

    if company.dirigeants:
        profile.dirigeants = [
            {"nom": leader.nom, "qualite": leader.qualite} for leader in company.dirigeants
        ]
        sources["dirigeants"] = _stamp("registry", at)
        changed.append("dirigeants")

    profile.field_sources = sources
    profile.updated_at = at

    if is_valid_siren(company.siren):
        await legal_identifiers_repository.upsert(
            session,
            organization_id=organization_id,
            pays=VAT_COUNTRY,
            schema=IDENTIFIER_SCHEMA_VAT,
            valeur=french_vat_number(company.siren),
            source="computed",
        )

    await session.flush()
    if diverged:
        await audit_service.record(
            session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action="legal.profile.diverged",
            resource_type="legal_profile",
            resource_id=str(profile.id),
            payload={"fields": diverged},
        )
    await audit_service.record(
        session,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="legal.profile.refreshed",
        resource_type="legal_profile",
        resource_id=str(profile.id),
        payload={
            "siren": company.siren,
            "diffusable": company.diffusable,
            "changed": changed,
        },
    )
    return await _out_from_row(
        session,
        profile=profile,
        organization_siren=company.siren,
        include_directors=True,
    )


def _merge_registry_value(
    profile: LegalProfile,
    sources: dict[str, Any],
    *,
    field: str,
    new_value: Any,
    at: datetime,
    changed: list[str],
    diverged: list[dict[str, Any]],
) -> None:
    """Fusionne un champ alimenté par le registre, en respectant la saisie manuelle.

    `manual` gagne toujours : un écart nourrit `diverged` (alerte) sans écraser.
    Sinon le registre met à jour la valeur et sa provenance, et note le changement.
    """
    current = getattr(profile, field)
    if sources.get(field, {}).get("source") == "manual" and current is not None:
        if current != new_value:
            diverged.append(
                {
                    "field": field,
                    "manual": current.isoformat() if isinstance(current, date) else current,
                    "registry": new_value.isoformat() if isinstance(new_value, date) else new_value,
                }
            )
        return
    if current != new_value:
        changed.append(field)
    setattr(profile, field, new_value)
    sources[field] = _stamp("registry", at)


async def _out_from_row(
    session: AsyncSession,
    *,
    profile: LegalProfile,
    organization_siren: str | None,
    include_directors: bool,
) -> LegalProfileOut:
    """Sérialise une fiche qui vient d'être écrite (identifiants relus en base)."""
    identifiers = await legal_identifiers_repository.list_for_organization(
        session, profile.organization_id
    )
    return _to_out(
        siren=profile.siren or organization_siren,
        values={field: getattr(profile, field) for field in LEGAL_PROFILE_TEXT_FIELDS},
        field_sources=dict(profile.field_sources or {}),
        dirigeants=[LegalDirectorOut(**item) for item in (profile.dirigeants or [])],
        date_creation=profile.date_creation,
        identifiers=identifiers,
        updated_at=profile.updated_at,
        include_directors=include_directors,
    )


def _to_out(
    *,
    siren: str | None,
    values: dict[str, Any],
    field_sources: dict[str, Any],
    dirigeants: list[LegalDirectorOut],
    identifiers: list[LegalIdentifier],
    updated_at: datetime | None,
    include_directors: bool,
    date_creation: date | None = None,
) -> LegalProfileOut:
    """Assemble la réponse publique : dirigeants masqués hors admin (SPEC §3)."""
    sources = {
        name: FieldSourceOut(source=entry.get("source", ""), synced_at=entry.get("synced_at"))
        for name, entry in field_sources.items()
        if isinstance(entry, dict)
    }
    return LegalProfileOut(
        siren=siren,
        date_creation=values.get("date_creation", date_creation),
        dirigeants=dirigeants if include_directors else [],
        sources=sources,
        identifiers=[_identifier_out(item) for item in identifiers],
        updated_at=updated_at,
        **{field: values.get(field) for field in LEGAL_PROFILE_TEXT_FIELDS},
    )


def _identifier_out(identifier: LegalIdentifier) -> LegalIdentifierOut:
    return LegalIdentifierOut(
        pays=identifier.pays,
        schema_name=identifier.schema,
        valeur=identifier.valeur,
        source=identifier.source,
        verified_at=identifier.verified_at,
    )
