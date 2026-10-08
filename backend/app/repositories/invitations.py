"""Repository : invitations (jeton haché, expiration, acceptation)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation


async def create_invitation(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    invited_by_id: uuid.UUID,
    email: str,
    role: str,
    module_permissions: list[dict[str, Any]],
    token_hash: str,
    expires_at: datetime,
) -> Invitation:
    """Crée une invitation en attente. Flush seulement."""
    invitation = Invitation(
        organization_id=organization_id,
        invited_by_id=invited_by_id,
        email=email,
        role=role,
        module_permissions=module_permissions,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(invitation)
    await session.flush()
    return invitation


async def get_by_token_hash(
    session: AsyncSession, *, token_hash: str, organization_id: uuid.UUID
) -> Invitation | None:
    """Jeton dans l'organisation courante : la RLS impose le tenant posé."""
    result = await session.execute(
        select(Invitation).where(
            Invitation.token_hash == token_hash,
            Invitation.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def get_pending_by_email(
    session: AsyncSession, *, organization_id: uuid.UUID, email: str
) -> Invitation | None:
    """Invitation toujours valable pour cet e-mail : seule elle bloque une nouvelle émission."""
    result = await session.execute(
        select(Invitation).where(
            Invitation.organization_id == organization_id,
            func.lower(Invitation.email) == email.lower(),
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def list_pending(session: AsyncSession, *, organization_id: uuid.UUID) -> list[Invitation]:
    """Invitations en attente et non expirées, les plus récentes en premier."""
    now = datetime.now(UTC)
    result = await session.execute(
        select(Invitation)
        .where(
            Invitation.organization_id == organization_id,
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > now,
        )
        .order_by(Invitation.created_at.desc(), Invitation.id)
    )
    return list(result.scalars().all())


async def get_by_id(
    session: AsyncSession, *, organization_id: uuid.UUID, invitation_id: uuid.UUID
) -> Invitation | None:
    """Invitation par identifiant, dans l'organisation de la route."""
    result = await session.execute(
        select(Invitation).where(
            Invitation.organization_id == organization_id,
            Invitation.id == invitation_id,
        )
    )
    return result.scalar_one_or_none()


async def mark_accepted(session: AsyncSession, invitation: Invitation) -> None:
    """Consomme l'invitation : elle ne peut plus être rejouée. Flush seulement."""
    invitation.accepted_at = datetime.now(UTC)
    await session.flush()


async def delete(session: AsyncSession, invitation: Invitation) -> None:
    """Supprime une invitation (révocation avant acceptation). Flush seulement."""
    await session.delete(invitation)
    await session.flush()
