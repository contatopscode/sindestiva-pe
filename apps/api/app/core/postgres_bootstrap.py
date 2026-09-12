"""Idempotent Postgres schema + extensions bootstrap (Coolify / fresh DB).

Docker Compose runs `infra/postgres/init.sql` on first init; managed
Postgres (Coolify HOM) does not. Alembic 0001 also runs CREATE EXTENSION,
but lifespan `create_all` and GIN indexes need `pg_trgm` before any DDL
that references `gin_trgm_ops`.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

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

# User-facing drift anchors (HOM incidents).
DRIFT_ANCHOR_TABLES: tuple[str, ...] = ("portos", "lousa_escala_origem")

REVISION_0001 = "0001_initial_lousa_main"
REVISION_0002 = "0002_lousa_escala_origem"
REVISION_HEAD = "0003_lousa_alocacao"


@dataclass(frozen=True)
class AlembicRunResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def combined_log(self) -> str:
        return (self.stdout or "") + (self.stderr or "")


def alembic_bin_path() -> str:
    return shutil.which("alembic") or "/app/.venv/bin/alembic"


def database_fingerprint(
    engine: Engine,
    *,
    schema: str | None = None,
) -> dict[str, str | None]:
    """Identifica o banco usado na verificação pós-migrate (mesma URL do Alembic)."""
    db_schema = schema or settings.db_schema
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT current_database()::text, current_user::text, "
                "current_setting('search_path')::text"
            ),
        ).one()
        has_version = conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_schema = :schema AND table_name = 'alembic_version'"
                ")"
            ),
            {"schema": db_schema},
        ).scalar()
    return {
        "database": row[0],
        "user": row[1],
        "search_path": row[2],
        "alembic_version_table_exists": str(bool(has_version)),
    }


def scan_alembic_log_for_errors(log_text: str) -> list[str]:
    """Extrai linhas de erro mesmo quando o CLI retorna rc=0 (rollback silencioso)."""
    needles = (
        "Traceback",
        "ERROR",
        "UndefinedObject",
        "UndefinedTable",
        "ProgrammingError",
        "InternalError",
        "failed",
    )
    hits: list[str] = []
    for line in log_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(n in stripped for n in needles):
            hits.append(stripped[:500])
    return hits[:20]


def run_alembic_cli(
    *args: str,
    cwd: str = "/app",
    timeout: int = 600,
) -> AlembicRunResult:
    proc = subprocess.run(
        [alembic_bin_path(), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return AlembicRunResult(proc.returncode, proc.stdout or "", proc.stderr or "")


def compute_stamp_target_for_missing(missing: list[str]) -> str | None:
    """Alembic `stamp` target to re-apply missing migrations (no downgrade DDL).

    Returns `base` to clear version and re-run from 0001, a revision id to
    re-run subsequent migrations, or None when a plain `upgrade head` suffices.
    """
    if not missing:
        return None
    if "portos" in missing:
        return "base"
    if "lousa_escala_origem" in missing:
        return REVISION_0001
    if "lousa_alocacao" in missing:
        return REVISION_0002
    return None


def detect_schema_drift(
    engine: Engine,
    *,
    schema: str | None = None,
) -> dict[str, object]:
    """True when alembic_version is set but critical tables are absent."""
    revision = get_alembic_revision(engine, schema=schema)
    missing = list_missing_critical_tables(engine, schema=schema)
    anchor_missing = [t for t in missing if t in DRIFT_ANCHOR_TABLES]
    drift = revision is not None and len(missing) > 0
    return {
        "revision": revision,
        "missing_tables": missing,
        "anchor_missing": anchor_missing,
        "drift": drift,
        "stamp_target": compute_stamp_target_for_missing(missing) if drift else None,
    }


def ensure_tables_via_metadata(
    engine: Engine,
    *,
    schema: str | None = None,
) -> None:
    """Fallback DDL when Alembic thinks it is at head but tables are missing."""
    from app.core.database import Base
    import app.models  # noqa: F401

    db_schema = schema or settings.db_schema
    with engine.begin() as conn:
        conn.execute(text(f"SET search_path TO {db_schema}, public"))
        Base.metadata.create_all(conn, checkfirst=True)


def run_migrations_with_drift_repair(
    *,
    url: str | None = None,
    schema: str | None = None,
    cwd: str = "/app",
) -> dict[str, object]:
    """Extensions must already exist. Runs Alembic with safe stamp repair."""
    db_url = url or settings.database_url_sync
    engine = create_engine(db_url, pool_pre_ping=True)
    actions: list[str] = []
    logs: list[str] = []

    try:
        before = detect_schema_drift(engine, schema=schema)
        missing_before = list(before["missing_tables"])
        revision_before = before["revision"]

        stamp_target = before["stamp_target"]
        if before["drift"] and stamp_target is not None:
            stamp_res = run_alembic_cli("stamp", stamp_target, cwd=cwd)
            logs.append(stamp_res.combined_log)
            actions.append(f"stamp:{stamp_target}")
            if stamp_res.returncode != 0:
                return {
                    "ok": False,
                    "actions": actions,
                    "revision_before": revision_before,
                    "revision_after": get_alembic_revision(engine, schema=schema),
                    "missing_before": missing_before,
                    "missing_after": list_missing_critical_tables(engine, schema=schema),
                    "log_tail": "\n".join(logs)[-3000:],
                    "error": f"alembic stamp {stamp_target} failed (rc={stamp_res.returncode})",
                }

        upgrade_res = run_alembic_cli("upgrade", "head", cwd=cwd)
        logs.append(upgrade_res.combined_log)
        actions.append("upgrade:head")
        log_errors = scan_alembic_log_for_errors(upgrade_res.combined_log)
        if upgrade_res.returncode != 0:
            return {
                "ok": False,
                "actions": actions,
                "revision_before": revision_before,
                "revision_after": get_alembic_revision(engine, schema=schema),
                "missing_before": missing_before,
                "missing_after": list_missing_critical_tables(engine, schema=schema),
                "log_tail": "\n".join(logs)[-3000:],
                "alembic_log_errors": log_errors,
                "db_fingerprint": database_fingerprint(engine, schema=schema),
                "error": f"alembic upgrade head failed (rc={upgrade_res.returncode})",
            }

        missing_after = list_missing_critical_tables(engine, schema=schema)
        revision_after = get_alembic_revision(engine, schema=schema)
        fingerprint = database_fingerprint(engine, schema=schema)

        if missing_after and upgrade_res.returncode == 0:
            hint = (
                "alembic upgrade reported success but critical tables are missing "
                "(historically: async run_sync without commit rolled back DDL)"
            )
            return {
                "ok": False,
                "repaired_drift": bool(before["drift"]),
                "actions": actions,
                "revision_before": revision_before,
                "revision_after": revision_after,
                "missing_before": missing_before,
                "missing_after": missing_after,
                "log_tail": "\n".join(logs)[-3000:],
                "alembic_log_errors": log_errors,
                "db_fingerprint": fingerprint,
                "error": hint,
            }

        if missing_after:
            try:
                ensure_tables_via_metadata(engine)
                actions.append("create_all:checkfirst")
            except Exception as exc:  # noqa: BLE001
                logs.append(f"create_all fallback failed: {exc}")

        missing_after = list_missing_critical_tables(engine, schema=schema)
        revision_after = get_alembic_revision(engine, schema=schema)
        ok = len(missing_after) == 0

        return {
            "ok": ok,
            "repaired_drift": bool(before["drift"]),
            "actions": actions,
            "revision_before": revision_before,
            "revision_after": revision_after,
            "missing_before": missing_before,
            "missing_after": missing_after,
            "log_tail": "\n".join(logs)[-3000:],
            "alembic_log_errors": log_errors,
            "db_fingerprint": fingerprint,
            "error": None if ok else "critical tables still missing after migrate/repair",
        }
    finally:
        engine.dispose()


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
