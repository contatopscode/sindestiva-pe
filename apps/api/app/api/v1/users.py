"""SINDESTIVA-PE · /users (CRUD admin)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", summary="Lista users (admin)")
async def list_users(
    db: AsyncSession = Depends(get_db),  # noqa: ARG001
    _admin_id: str = Depends(require_user),  # apenas autenticado
) -> dict[str, list]:
    """Sprint 0: retorna lista vazia. Sprint 1 T1-04: SELECT real."""
    return {"items": [], "total": 0}


@router.get("/{user_id}", summary="Detalhe de um user")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: ARG001
    _caller: str = Depends(require_user),
) -> dict[str, str]:
    """Sprint 0: stub. Sprint 1: SELECT real."""
    return {"id": user_id, "stub": "true"}
