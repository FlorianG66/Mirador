"""Fournisseur LLM interchangeable du chatbot (SPEC §4, phase 8).

Le service de chat ne parle qu'au protocole `LlmProvider` : un tour de modèle
renvoie du texte et/ou des appels d'outils. `AnthropicProvider` est l'implémentation
par défaut (SDK officiel) ; les tests et la CI injectent un faux fournisseur sur
`app.state.llm_provider`, sans réseau ni vraie clé (AGENTS.md §5). Les messages
suivent le format de l'API Messages d'Anthropic : un autre fournisseur traduira
ce format dans son adaptateur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, cast

import anthropic

# Réponses de chat courtes : un effort bas suffit et limite le coût (quotas).
_EFFORT = "low"
_MAX_TOKENS = 16000


class LlmError(Exception):
    """Le fournisseur n'a pas pu répondre (réseau, quota fournisseur, refus)."""


@dataclass(frozen=True)
class ToolCall:
    """Un appel d'outil demandé par le modèle."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class LlmTurn:
    """Un tour du modèle : texte final et/ou appels d'outils à exécuter.

    `assistant_content` est renvoyé tel quel au tour suivant (blocs d'outils et de
    raisonnement compris) : le fournisseur exige l'historique intact.
    """

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    assistant_content: Any = None


class LlmProvider(Protocol):
    """Contrat minimal d'un fournisseur : un tour de conversation avec outils."""

    async def respond(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LlmTurn: ...


class AnthropicProvider:
    """Fournisseur Claude via le SDK officiel (fallback serveur sur refus activé)."""

    def __init__(
        self, *, api_key: str, model: str, client: anthropic.AsyncAnthropic | None = None
    ) -> None:
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def respond(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LlmTurn:
        """Un appel à l'API Messages ; lève `LlmError` sur échec ou refus."""
        try:
            response = await self._client.beta.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=system,
                messages=cast(Any, messages),
                tools=cast(Any, tools),
                output_config=cast(Any, {"effort": _EFFORT}),
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.APIError as exc:
            raise LlmError(type(exc).__name__) from exc
        if response.stop_reason == "refusal":
            raise LlmError("refusal")
        return LlmTurn(
            text="\n".join(block.text for block in response.content if block.type == "text"),
            tool_calls=[
                ToolCall(id=block.id, name=block.name, input=dict(block.input))
                for block in response.content
                if block.type == "tool_use"
            ],
            assistant_content=response.content,
        )
