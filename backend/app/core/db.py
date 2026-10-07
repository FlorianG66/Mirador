"""Accès à PostgreSQL : vérification de connexion et version du serveur."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

# Assez court pour une sonde de santé, assez large pour une base chargée.
CONNECT_TIMEOUT_SECONDS = 5


class DatabaseUnavailableError(RuntimeError):
    """PostgreSQL est injoignable ou refuse la connexion."""


async def get_database_version(database_url: str) -> str:
    """Retourne la bannière de version du serveur PostgreSQL.

    Lève DatabaseUnavailableError si la base est injoignable.
    """
    engine = create_async_engine(database_url, connect_args={"timeout": CONNECT_TIMEOUT_SECONDS})
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT version()"))
            return str(result.scalar_one())
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        raise DatabaseUnavailableError(f"impossible de joindre la base : {exc}") from exc
    finally:
        await engine.dispose()
