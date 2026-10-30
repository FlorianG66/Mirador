"""Routes du chatbot IA (phase 8) : historique et question, personnels à l'appelant.

Aucun droit de module exigé ici : chaque outil appelé par le modèle revérifie
les droits du membre (service). Aucun try/except : les refus remontent en
`ServiceProblem` (503 non configuré, 429 quota, 502 fournisseur en échec).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import get_request_settings, get_session
from app.core.permissions import get_current_tenant
from app.models.membership import Membership
from app.schemas.chat import ChatMessageOut, ChatQuestionIn
from app.services import chat as chat_service

router = APIRouter(prefix="/organizations/{organization_id}/chat")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
CurrentTenant = Annotated[Membership, Depends(get_current_tenant)]
RequestSettings = Annotated[Settings, Depends(get_request_settings)]


@router.get("/messages", response_model=list[ChatMessageOut])
async def list_messages(
    session: SessionDependency, membership: CurrentTenant
) -> list[ChatMessageOut]:
    """Historique personnel de l'appelant dans l'organisation."""
    return await chat_service.list_history(session, membership=membership)


@router.post("/messages", response_model=list[ChatMessageOut], status_code=201)
async def ask(
    payload: ChatQuestionIn,
    request: Request,
    session: SessionDependency,
    membership: CurrentTenant,
    settings: RequestSettings,
) -> list[ChatMessageOut]:
    """Pose une question ; renvoie la question et la réponse enregistrées."""
    return await chat_service.ask(
        session,
        membership=membership,
        provider=request.app.state.llm_provider,
        settings=settings,
        question=payload.content,
    )
