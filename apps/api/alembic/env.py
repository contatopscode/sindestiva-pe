"""SINDESTIVA-PE · Alembic environment (sync online migrations).

ATENÇÃO — pega-dica cross-projeto (MEMORY do coder agent):
    NUNCA usar `asyncio.run()` dentro de lifespan FastAPI — quebra em
    prod porque o event loop já está ativo.

ATENÇÃO — Coolify HOM (2026-09):
    1) NÃO usar `async_engine` + `run_sync` sem `await connection.commit()`.
    2) NÃO usar só `engine.connect()` — no SQLAlchemy 2 o `__exit__` dá
       ROLLBACK na transação externa; use `engine.begin()` para COMMIT.
    Migrations online: sync `create_engine` + `with connectable.begin()`.

Convenção: target_metadata = `app.models.base.Base.metadata`.
Schema target = `lousa_main` (default do init.sql do container).
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

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


def run_migrations_online() -> None:
    """Modo online — sync engine; `begin()` faz COMMIT ao sair com sucesso."""
    connectable = create_engine(
        settings.database_url_sync,
        poolclass=pool.NullPool,
    )
    # SA 2: `connect().__exit__` rollback — `begin().__exit__` commit.
    with connectable.begin() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
