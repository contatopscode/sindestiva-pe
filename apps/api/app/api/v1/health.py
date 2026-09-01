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
