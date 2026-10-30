"""Schémas du mode démo (SPEC §9) : scénarios, session, liens à durée limitée."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import DemoSector
from app.schemas.auth import OrganizationOut, UserOut


class DemoScenarioOut(BaseModel):
    """Un scénario sectoriel proposé sur `/demo`."""

    key: DemoSector
    organization_name: str


class DemoSessionRequest(BaseModel):
    """Ouverture d'une session de démonstration depuis `/demo`."""

    sector: DemoSector


class DemoLinkRequest(BaseModel):
    """Génération d'un lien pour un prospect, sur un secteur donné."""

    sector: DemoSector


class DemoSessionResponse(BaseModel):
    """Session de démonstration ouverte : même forme qu'une inscription."""

    user: UserOut
    organization: OrganizationOut
    sector: DemoSector
    expires_at: datetime


class DemoLinkOut(BaseModel):
    """Lien de démonstration : le jeton en clair n'est montré qu'une seule fois."""

    token: str
    path: str
    url: str
    sector: DemoSector
    expires_at: datetime
