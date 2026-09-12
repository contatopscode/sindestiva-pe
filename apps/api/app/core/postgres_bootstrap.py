"""Idempotent Postgres schema + extensions bootstrap (Coolify / fresh DB).

Docker Compose runs `infra/postgres/init.sql` on first init; managed
Postgres (Coolify HOM) does not. Alembic 0001 also runs CREATE EXTENSION,
but lifespan `create_all` and GIN indexes need `pg_trgm` before any DDL
that references `gin_trgm_ops`.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ProgrammingError

from app.core.config import settings

# Keep in sync with alembic/versions/0001_initial_lousa_main.py §1
POSTGRES_EXTENSIONS: tuple[str, ...] = ("pgcrypto", "citext", "pg_trgm")

# Tables used to detect alembic_version ahead of real DDL (repair hint).
CRITICAL_TABLES: tuple[str, ...] = (
    "portos",
    "users",
    "lousa_escala_origem",
    "lousa_alocacao",
)


def ensure_schema_and_extensions(
    *,
    url: str | None = None,
    schema: str | None = None,
) -> dict[str, object]:
    """CREATE SCHEMA + CREATE EXTENSION IF NOT EXISTS (sync, idempotent).

    Uses AUTOCOMMIT for extensions (same pattern as many managed PG guides).
    Raises on permission errors so entrypoint can fail fast.
    """
    db_url = url or settings.database_url_sync
    db_schema = schema or settings.db_schema
    engine = create_engine(db_url, pool_pre_ping=True)

    extensions_applied: list[str] = []
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {db_schema}"))
        conn.commit()

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for ext in POSTGRES_EXTENSIONS:
            conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{ext}"'))
            extensions_applied.append(ext)

    engine.dispose()
    return {
        "schema": db_schema,
        "extensions": extensions_applied,
    }


def list_missing_critical_tables(
    engine: Engine,
    *,
    schema: str | None = None,
) -> list[str]:
    """Return critical table names absent from information_schema."""
    db_schema = schema or settings.db_schema
    missing: list[str] = []
    with engine.connect() as conn:
        for table in CRITICAL_TABLES:
            row = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table "
                    "LIMIT 1"
                ),
                {"schema": db_schema, "table": table},
            ).first()
            if row is None:
                missing.append(table)
    return missing


def get_alembic_revision(engine: Engine, *, schema: str | None = None) -> str | None:
    """Current Alembic revision in `lousa_main.alembic_version`, if any."""
    db_schema = schema or settings.db_schema
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT version_num FROM {db_schema}.alembic_version LIMIT 1"
                ),
            ).first()
        return row[0] if row else None
    except ProgrammingError:
        return None
