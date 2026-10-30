"""Service du chatbot IA (SPEC §4, phase 8) : boucle d'outils en lecture seule.

Le modèle ne voit jamais la base : il appelle deux outils, exécutés ici avec les
droits du membre courant. `list_metrics` ne liste que les modules visibles ;
`get_metric_comparison` revérifie l'accès `view` au module de la clé avant toute
lecture — un refus revient au modèle comme erreur d'outil, sans aucune donnée.
Seuls la question et la réponse finale sont conservées (historique personnel),
et le quota journalier se compte sur ces questions.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, time
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import PROJECT_NAME
from app.core.permissions import ensure_module_access, modules_for
from app.models.enums import Module, PermissionLevel
from app.models.membership import Membership
from app.repositories import chat_messages as chat_messages_repository
from app.repositories import module_permissions as module_permissions_repository
from app.repositories import organizations as organizations_repository
from app.schemas.chat import ChatMessageOut
from app.services import metrics as metrics_service
from app.services.errors import ServiceProblem
from app.services.llm import LlmError, LlmProvider, ToolCall
from app.services.metric_catalog import METRIC_AGGREGATIONS

logger = logging.getLogger(__name__)

# Messages d'historique renvoyés au modèle : assez pour le contexte, coût borné.
HISTORY_LIMIT = 20
# Tours d'outils maximum par question : coupe une boucle qui ne converge pas.
MAX_TOOL_ROUNDS = 6
MAX_COMPARISON_DAYS = 365

SYSTEM_PROMPT = (
    f"Tu es l'assistant de {PROJECT_NAME}, un tableau de bord d'entreprise. Tu réponds "
    "aux questions sur les données de l'entreprise de l'utilisateur, dans la langue de "
    "sa question, en quelques phrases. Utilise les outils pour lire les chiffres : "
    "n'invente jamais une valeur. Si un outil refuse l'accès ou ne trouve pas de "
    "donnée, dis-le simplement. Tu es en lecture seule : tu ne peux rien modifier."
)

TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_metrics",
        "description": (
            "Liste les clés de métriques que l'utilisateur a le droit de consulter "
            "(format module.metrique, ex. finance.revenue). À appeler d'abord."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_metric_comparison",
        "description": (
            "Valeur agrégée d'une métrique sur les `days` derniers jours, comparée aux "
            "`days` jours précédents (valeurs, écart et écart en %, unité)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_key": {"type": "string"},
                "days": {"type": "integer", "minimum": 1, "maximum": MAX_COMPARISON_DAYS},
            },
            "required": ["metric_key", "days"],
            "additionalProperties": False,
        },
    },
]


async def list_history(session: AsyncSession, *, membership: Membership) -> list[ChatMessageOut]:
    """Historique personnel du membre (les derniers messages, ordre chronologique)."""
    rows = await chat_messages_repository.list_recent(
        session,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        limit=HISTORY_LIMIT,
    )
    return [ChatMessageOut.model_validate(row, from_attributes=True) for row in rows]


async def ask(
    session: AsyncSession,
    *,
    membership: Membership,
    provider: LlmProvider | None,
    settings: Settings,
    question: str,
) -> list[ChatMessageOut]:
    """Répond à une question ; renvoie la question et la réponse enregistrées."""
    if provider is None:
        raise ServiceProblem(503, "Assistant IA non configuré.")
    await _check_quota(session, membership=membership, settings=settings)

    history = await chat_messages_repository.list_recent(
        session,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        limit=HISTORY_LIMIT,
    )
    messages: list[dict[str, Any]] = [{"role": row.role, "content": row.content} for row in history]
    messages.append({"role": "user", "content": question})
    answer = await _run(session, membership=membership, provider=provider, messages=messages)

    saved = [
        await chat_messages_repository.add(
            session,
            organization_id=membership.organization_id,
            user_id=membership.user_id,
            role=role,
            content=content,
        )
        for role, content in (("user", question), ("assistant", answer))
    ]
    return [ChatMessageOut.model_validate(row, from_attributes=True) for row in saved]


async def _check_quota(
    session: AsyncSession, *, membership: Membership, settings: Settings
) -> None:
    """429 au-delà du quota du jour (UTC) ; plafond réduit pour une organisation démo."""
    organization = await organizations_repository.get_organization(
        session, membership.organization_id
    )
    is_demo = organization is not None and organization.is_demo
    quota = settings.chat_demo_daily_quota if is_demo else settings.chat_daily_quota
    since = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
    asked = await chat_messages_repository.count_questions_since(
        session,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        since=since,
    )
    if asked >= quota:
        raise ServiceProblem(429, "Quota quotidien de questions atteint.")


async def _run(
    session: AsyncSession,
    *,
    membership: Membership,
    provider: LlmProvider,
    messages: list[dict[str, Any]],
) -> str:
    """Boucle modèle ↔ outils jusqu'à une réponse texte (bornée à MAX_TOOL_ROUNDS)."""
    for _ in range(MAX_TOOL_ROUNDS):
        try:
            turn = await provider.respond(system=SYSTEM_PROMPT, messages=messages, tools=TOOLS)
        except LlmError as exc:
            # Jamais la question dans les journaux (données personnelles possibles).
            logger.warning("Assistant IA en échec : %s", exc)
            raise ServiceProblem(502, "L'assistant IA n'a pas pu répondre.") from exc
        if not turn.tool_calls:
            return turn.text
        messages.append({"role": "assistant", "content": turn.assistant_content})
        messages.append(
            {
                "role": "user",
                "content": [
                    await _tool_result(session, membership, call) for call in turn.tool_calls
                ],
            }
        )
    raise ServiceProblem(502, "L'assistant IA n'a pas pu répondre.")


async def _tool_result(
    session: AsyncSession, membership: Membership, call: ToolCall
) -> dict[str, Any]:
    """Exécute un outil et le met au format `tool_result` (erreur si refus)."""
    try:
        content = await _execute(session, membership, call)
        is_error = False
    except (HTTPException, ServiceProblem, ValueError) as exc:
        content = getattr(exc, "detail", None) or "Requête invalide."
        is_error = True
    return {
        "type": "tool_result",
        "tool_use_id": call.id,
        "content": content,
        "is_error": is_error,
    }


async def _execute(session: AsyncSession, membership: Membership, call: ToolCall) -> str:
    """Les deux outils en lecture seule ; toute lecture passe par les droits du membre."""
    if call.name == "list_metrics":
        modules = await _effective_modules(session, membership)
        visible = {
            module.value for module, level in modules.items() if level != PermissionLevel.NONE
        }
        return json.dumps(
            sorted(key for key in METRIC_AGGREGATIONS if key.split(".")[0] in visible)
        )
    if call.name == "get_metric_comparison":
        metric_key = str(call.input.get("metric_key", ""))
        days = int(call.input.get("days", 0))
        if not 1 <= days <= MAX_COMPARISON_DAYS:
            raise ValueError("days")
        module = Module(metric_key.split(".")[0])  # ValueError si module inconnu
        await ensure_module_access(session, membership, module, PermissionLevel.VIEW)
        comparison = await metrics_service.get_metric_comparison(
            session, membership.organization_id, metric_key, days=days
        )
        return json.dumps(
            {
                "metric_key": comparison.key,
                "unit": comparison.unit,
                "aggregation": comparison.aggregation.value,
                "days": comparison.days,
                **comparison.summary.model_dump(),
            }
        )
    raise ValueError(call.name)


async def _effective_modules(
    session: AsyncSession, membership: Membership
) -> dict[Module, PermissionLevel]:
    """Niveaux effectifs du membre : stocké, ou `edit` partout pour un admin."""
    rows = await module_permissions_repository.list_for_membership(
        session, membership_id=membership.id
    )
    choices = {Module(row.module): PermissionLevel(row.level) for row in rows}
    return modules_for(membership.role, choices)
