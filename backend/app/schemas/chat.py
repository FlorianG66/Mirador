"""Schémas du chatbot IA (phase 8) : question entrante, messages de l'historique."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Une question tient en quelques phrases : borne le coût et la surface d'injection.
CHAT_QUESTION_MAX_LENGTH = 2000


class ChatQuestionIn(BaseModel):
    """Question posée en langage naturel."""

    content: str = Field(min_length=1, max_length=CHAT_QUESTION_MAX_LENGTH)


class ChatMessageOut(BaseModel):
    """Un message de l'historique (question ou réponse)."""

    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
