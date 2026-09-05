"""SINDESTIVA-PE · /health endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api.deps import get_db
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Liveness + DB ping")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Liveness + ping no schema `lousa_main`.

    Sprint 0: ping simples. Sprint 7: adiciona check de Redis + scraper.
    """
    try:
        await db.execute(text("SELECT 1 FROM lousa_main.users LIMIT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001
        db_status = "down"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "sindestiva-api",
        "version": "0.1.0",
        "env": settings.app_env,
        "db": db_status,
    }


@router.get("/diag", summary="Diagnóstico de schema/tabelas (debug)")
async def diag(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """Lista schemas, tabelas e current_schema do DB. Usado para
    debugar conexão em produção (Render, etc).
    """
    schemas = [
        r[0]
        for r in (await db.execute(
            text("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
        )).all()
    ]
    tables = [
        r[0]
        for r in (await db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :s ORDER BY table_name"
            ),
            {"s": settings.db_schema},
        )).all()
    ]
    current_schema = (await db.execute(text("SELECT current_schema()"))).scalar()
    # Lista tabelas em TODOS os schemas (para debugar se o alemic_version
    # foi parar em public em vez de lousa_main).
    all_tables = [
        {"schema": r[0], "table": r[1]}
        for r in (await db.execute(text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY table_schema, table_name"
        ))).all()
    ]
    return {
        "current_schema": current_schema,
        "expected_schema": settings.db_schema,
        "schemas": schemas,
        "tables_in_expected_schema": tables,
        "all_tables": all_tables,
        "database_url_host": settings.database_url_async.split("@")[-1].split("/")[0],
    }
