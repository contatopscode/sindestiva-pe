"""SINDESTIVA-PE · Database (SQLAlchemy 2 async + asyncpg).

Pega-dica (cross-projeto, MEMORY): NUNCA usar `asyncio.run()` dentro do
lifespan FastAPI — quebra em prod porque o event loop já está ativo.
Usar `AsyncSessionLocal` direto. Este módulo não expõe helpers que
façam isso.

Schema default = `lousa_main` (ADR-002 — schema único no MVP).
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base do SINDESTIVA-PE (SQLAlchemy 2).

    Importado também de `app.models.base` para re-export estável.
    Aqui fica a definição canônica para evitar import circular.
    """


# ---------------------------------------------------------------------------
# Engine + sessionmaker
# ---------------------------------------------------------------------------

def _build_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url_async,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,  # detecta conexão morta (importante pra scraper)
        future=True,
    )


engine: AsyncEngine = _build_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)


# ---------------------------------------------------------------------------
# Dependencies (FastAPI) e helper de contexto
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency FastAPI: yield de uma sessão async.

    Uso:
        @router.get(...)
        async def endpoint(db: AsyncSession = Depends(get_db)): ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager para uso fora de FastAPI (jobs, scripts, CLI).

    Uso:
        async with session_scope() as session:
            session.add(obj)
            await session.commit()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Helpers de schema (search_path)
# ---------------------------------------------------------------------------

# Necessário porque o `init.sql` do container define o search_path por
# DATABASE, mas ao conectar via asyncpg o search_path volta ao default
# do role (`"$user", public`). Sem isso, queries falham com
# `relation "lousa_main.users" does not exist`. Hook no sync_engine
# subjacente do AsyncEngine — é o único ponto onde temos uma conexão
# DBAPI real.
from sqlalchemy import event  # noqa: E402


@event.listens_for(engine.sync_engine, "connect")
def _set_search_path(dbapi_connection, connection_record):  # noqa: ARG001
    """Ao abrir conexão, força search_path = lousa_main, public."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"SET search_path TO {settings.db_schema}, public")
    finally:
        cursor.close()


__all__ = [
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "session_scope",
]
