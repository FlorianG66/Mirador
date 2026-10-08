"""Garde de module : un membre sans accès au module reçoit 403 (critère de la phase 2).

Les routes de modules n'existent qu'en phase 4/5 : les probes ci-dessous branchent la
dépendance `require_module` sur de vraies routes HTTP pour tester le comportement réel.
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import Depends, FastAPI

from app.core.constants import API_PREFIX
from app.core.permissions import require_module
from app.models.enums import Module, PermissionLevel
from tests.conftest import register_client
from tests.helpers import invite_and_accept, register_admin


def install_probes(app: FastAPI) -> None:
    """Ajoute deux routes témoin : un garde `view` et un garde `edit` sur la finance."""

    async def view_probe() -> dict[str, str]:
        return {"guard": "view"}

    async def edit_probe() -> dict[str, str]:
        return {"guard": "edit"}

    app.add_api_route(
        f"{API_PREFIX}/organizations/{{organization_id}}/_probe/view",
        view_probe,
        methods=["GET"],
        dependencies=[Depends(require_module(Module.FINANCE, PermissionLevel.VIEW))],
    )
    app.add_api_route(
        f"{API_PREFIX}/organizations/{{organization_id}}/_probe/edit",
        edit_probe,
        methods=["GET"],
        dependencies=[Depends(require_module(Module.FINANCE, PermissionLevel.EDIT))],
    )


async def _probe(
    client: httpx.AsyncClient, organization_id: uuid.UUID, guard: str
) -> httpx.Response:
    return await client.get(f"{API_PREFIX}/organizations/{organization_id}/_probe/{guard}")


async def test_a_member_without_the_module_gets_403(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    install_probes(app)
    organization_id = await register_admin(client)
    await invite_and_accept(
        app, client, organization_id=organization_id, email="membre@example.com"
    )

    response = await _probe(client, organization_id, "view")

    assert response.status_code == 403
    assert response.json()["detail"] == "Accès « view » requis pour le module « finance »."


async def test_view_access_passes_the_view_guard_but_not_the_edit_guard(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    install_probes(app)
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="membre@example.com",
        modules={"finance": "view"},
    )

    as_viewer = await _probe(client, organization_id, "view")
    as_editor = await _probe(client, organization_id, "edit")

    assert as_viewer.status_code == 200
    assert as_editor.status_code == 403
    assert as_editor.json()["detail"] == "Accès « edit » requis pour le module « finance »."


async def test_edit_access_passes_both_guards(client: httpx.AsyncClient, app: FastAPI) -> None:
    install_probes(app)
    organization_id = await register_admin(client)
    await invite_and_accept(
        app,
        client,
        organization_id=organization_id,
        email="membre@example.com",
        modules={"finance": "edit"},
    )

    assert (await _probe(client, organization_id, "view")).status_code == 200
    assert (await _probe(client, organization_id, "edit")).status_code == 200


async def test_an_admin_bypasses_module_permissions(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    install_probes(app)
    organization_id = await register_admin(client)

    # L'admin n'a aucune ligne en base : son accès ne vient pas des permissions.
    assert (await _probe(client, organization_id, "view")).status_code == 200
    assert (await _probe(client, organization_id, "edit")).status_code == 200


async def test_a_non_member_of_the_organization_gets_403(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    install_probes(app)
    organization_id = await register_admin(client)
    await register_client(client, email="intrus@example.com")

    response = await _probe(client, organization_id, "view")

    assert response.status_code == 403
    assert response.json()["detail"] == "Vous n'avez pas accès à cette organisation."
