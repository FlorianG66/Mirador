"""Cycle de vie de l'application : le pool de connexions est libéré à l'arrêt."""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import text


async def test_lifespan_disposes_the_connection_pool(app: FastAPI) -> None:
    """Le lifespan ferme les connexions : rien ne reste ouvert après l'arrêt."""
    async with app.router.lifespan_context(app):
        async with app.state.engine.connect() as connection:
            assert (await connection.execute(text("SELECT 1"))).scalar_one() == 1
        assert "Connections in pool: 1" in app.state.engine.pool.status()

    assert "Connections in pool: 0" in app.state.engine.pool.status()
