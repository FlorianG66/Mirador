"""Tests du chatbot IA (phase 8).

Fournisseur LLM mocké (aucun réseau, aucune clé) : un faux fournisseur rejoue
des tours scriptés et garde les messages reçus, ce qui permet de vérifier
exactement ce que le modèle aurait vu. Couvre : assistant non configuré,
boucle d'outils, refus d'un module non autorisé (aucune donnée transmise),
liste des métriques restreinte, quota journalier, historique personnel, échec
du fournisseur et adaptateur Anthropic.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import API_PREFIX
from app.core.tenancy import set_tenant
from app.repositories import metric_snapshots as metric_snapshots_repository
from app.schemas.metrics import MetricSnapshotIn
from app.services.llm import AnthropicProvider, LlmError, LlmTurn, ToolCall
from tests.helpers import csrf_headers, invite_and_accept, login, register_admin


class FakeLlmProvider:
    """Rejoue des tours scriptés ; mémorise les messages reçus à chaque appel."""

    def __init__(self, *turns: LlmTurn, error: LlmError | None = None) -> None:
        self.turns = list(turns)
        self.error = error
        self.calls: list[list[dict[str, Any]]] = []

    async def respond(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LlmTurn:
        self.calls.append(json.loads(json.dumps(messages, default=str)))
        if self.error is not None:
            raise self.error
        return self.turns.pop(0)


def _url(organization_id: uuid.UUID) -> str:
    return f"{API_PREFIX}/organizations/{organization_id}/chat/messages"


def _tool(name: str, **arguments: object) -> LlmTurn:
    return LlmTurn(text="", tool_calls=[ToolCall(id=f"call-{name}", name=name, input=arguments)])


def _tool_results(provider: FakeLlmProvider) -> list[dict[str, Any]]:
    """Les `tool_result` renvoyés au modèle lors du dernier appel."""
    content: list[dict[str, Any]] = provider.calls[-1][-1]["content"]
    return content


async def _ask(
    client: httpx.AsyncClient, organization_id: uuid.UUID, question: str
) -> httpx.Response:
    return await client.post(
        _url(organization_id), json={"content": question}, headers=csrf_headers(client)
    )


async def _seed_revenue(db_session: AsyncSession, organization_id: uuid.UUID) -> None:
    """Dix jours de CA (1 → 10) : 7 jours courants = 4+…+10 = 49, précédents = 1+2+3."""
    now = datetime.now(UTC)
    await set_tenant(db_session, organization_id=organization_id)
    await metric_snapshots_repository.upsert_many(
        db_session,
        organization_id,
        [
            MetricSnapshotIn(
                metric_key="finance.revenue",
                unit="EUR",
                period="P1D",
                value=float(day + 1),
                captured_at=now - timedelta(days=9 - day, hours=12),
            )
            for day in range(10)
        ],
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_assistant_non_configure(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    app.state.llm_provider = None

    response = await _ask(client, organization_id, "Quel est mon CA ?")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_boucle_outils_et_historique(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_revenue(db_session, organization_id)
    provider = FakeLlmProvider(
        _tool("list_metrics"),
        _tool("get_metric_comparison", metric_key="finance.revenue", days=7),
        LlmTurn(text="Votre CA sur 7 jours est de 49 €."),
    )
    app.state.llm_provider = provider

    response = await _ask(client, organization_id, "Quel est mon CA ?")

    assert response.status_code == 201, response.text
    assert [m["role"] for m in response.json()] == ["user", "assistant"]
    assert response.json()[1]["content"] == "Votre CA sur 7 jours est de 49 €."
    listed = json.loads(provider.calls[1][-1]["content"][0]["content"])
    assert "finance.revenue" in listed and "web.sessions" in listed
    comparison = json.loads(_tool_results(provider)[0]["content"])
    assert comparison["current_value"] == 49.0
    history = await client.get(_url(organization_id))
    assert [m["content"] for m in history.json()] == [
        "Quel est mon CA ?",
        "Votre CA sur 7 jours est de 49 €.",
    ]


@pytest.mark.asyncio
async def test_module_non_autorise_ne_fuit_aucune_donnee(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    organization_id = await register_admin(client)
    await _seed_revenue(db_session, organization_id)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="web@example.com",
        modules={"web": "view"},
    )
    provider = FakeLlmProvider(
        _tool("list_metrics"),
        _tool("get_metric_comparison", metric_key="finance.revenue", days=7),
        LlmTurn(text="Je n'ai pas accès à la finance."),
    )
    app.state.llm_provider = provider

    response = await _ask(client, organization_id, "Quel est mon CA ?")

    assert response.status_code == 201, response.text
    listed = json.loads(provider.calls[1][-1]["content"][0]["content"])
    assert listed and all(key.startswith("web.") for key in listed)
    refused = _tool_results(provider)[0]
    assert refused["is_error"] is True
    assert "49" not in refused["content"]


@pytest.mark.asyncio
async def test_quota_journalier(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    app.state.settings = app.state.settings.model_copy(update={"chat_daily_quota": 1})
    app.state.llm_provider = FakeLlmProvider(LlmTurn(text="Bonjour."), LlmTurn(text="Encore."))

    assert (await _ask(client, organization_id, "Bonjour")).status_code == 201
    assert (await _ask(client, organization_id, "Encore ?")).status_code == 429


@pytest.mark.asyncio
async def test_historique_personnel(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    app.state.llm_provider = FakeLlmProvider(LlmTurn(text="Réponse privée."))
    assert (await _ask(client, organization_id, "Question privée")).status_code == 201

    await invite_and_accept(
        app, client, organization_id=organization_id, email="autre@example.com", modules={}
    )

    assert (await client.get(_url(organization_id))).json() == []
    await login(client, "admin@example.com")
    assert len((await client.get(_url(organization_id))).json()) == 2


@pytest.mark.asyncio
async def test_autre_organisation_refusee(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    client.cookies.clear()
    await register_admin(client, email="intrus@example.com")

    assert (await client.get(_url(organization_id))).status_code == 403


@pytest.mark.asyncio
async def test_echec_du_fournisseur(app: FastAPI, client: httpx.AsyncClient) -> None:
    organization_id = await register_admin(client)
    app.state.llm_provider = FakeLlmProvider(error=LlmError("APIConnectionError"))

    response = await _ask(client, organization_id, "Quel est mon CA ?")

    assert response.status_code == 502
    assert (await client.get(_url(organization_id))).json() == []


class _FakeMessages:
    def __init__(self, response: SimpleNamespace) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return self.response


def _anthropic(response: SimpleNamespace) -> tuple[AnthropicProvider, _FakeMessages]:
    messages = _FakeMessages(response)
    client: Any = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return AnthropicProvider(api_key="", model="claude-opus-5-5", client=client), messages


@pytest.mark.asyncio
async def test_adaptateur_anthropic_lit_texte_et_outils() -> None:
    content = [
        SimpleNamespace(type="text", text="Je regarde."),
        SimpleNamespace(type="tool_use", id="t1", name="list_metrics", input={}),
    ]
    provider, messages = _anthropic(SimpleNamespace(stop_reason="tool_use", content=content))

    turn = await provider.respond(system="s", messages=[], tools=[])

    assert turn.text == "Je regarde."
    assert turn.tool_calls == [ToolCall(id="t1", name="list_metrics", input={})]
    assert messages.kwargs["fallbacks"] == "default"


@pytest.mark.asyncio
async def test_adaptateur_anthropic_refus() -> None:
    provider, _ = _anthropic(SimpleNamespace(stop_reason="refusal", content=[]))

    with pytest.raises(LlmError):
        await provider.respond(system="s", messages=[], tools=[])
