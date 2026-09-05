"""SINDESTIVA-PE · Alembic environment (async + sync fallback).

ATENÇÃO — pega-dica cross-projeto (MEMORY do coder agent):
    NUNCA usar `asyncio.run()` dentro de lifespan FastAPI — quebra em
    prod porque o event loop já está ativo. Este `env.py` usa
    `connection.run_sync(do_migrations)` dentro de `asyncio.run()` no
    TOPO do script (chamado UMA VEZ por comando Alembic), o que é
    seguro. O problema seria instanciar engine async dentro de uma
    request ou lifespan handler.

Convenção: target_metadata = `app.models.base.Base.metadata`.
Schema target = `lousa_main` (default do init.sql do container).
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Import do projeto (config + Base + models)
# ---------------------------------------------------------------------------
from app.core.config import settings
from app.models.base import Base
import app.models  # noqa: F401  (popula Base.metadata com as 26 tabelas)

config = context.config

# Sobrescreve URL do ini com a do settings (lê do .env).
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def include_object(object, name, type_, reflected, compare_to):  # noqa: ARG001
    """Filtra objetos do schema `lousa_main` apenas.

    Evita que Alembic tente dropar/alterar objetos em `public` ou em
    schemas de outras ferramentas conectadas ao mesmo banco.
    """
    if type_ == "table" and object.schema != "lousa_main":
        return False
    if type_ == "index" and object.table is not None and object.table.schema != "lousa_main":
        return False
    return True


def run_migrations_offline() -> None:
    """Modo offline (gera SQL sem conectar). Útil pra revisar."""
    context.configure(
        url=settings.database_url_sync,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        version_table_schema="lousa_main",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Aplica migrations em uma conexão síncrona."""
    # Garante que o schema `lousa_main` existe antes de qualquer migration
    # rodar. Idempotente (`IF NOT EXISTS`). Em dev local, o init.sql do
    # docker-compose já cria; em prod (Render), o `sinapse-db` é
    # compartilhado com Sinapse e o schema do Sindestiva é criado aqui.
    connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS lousa_main")
    connection.exec_driver_sql("SET search_path TO lousa_main, public")
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        version_table_schema="lousa_main",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Modo online (conecta e aplica).

    Usa `async_engine_from_config` + `connection.run_sync(do_migrations)`.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Top-level asyncio.run — SEGURO aqui (comando Alembic standalone).
    asyncio.run(run_migrations_online())
