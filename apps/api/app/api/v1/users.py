"""SINDESTIVA-PE · /users (CRUD admin FISCAL + DIRIGENTE)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import get_current_user_id, get_current_user_role, oauth2_scheme
from app.schemas.user_admin import (
    AdminUserCreate,
    AdminUserListResponse,
    AdminUserRead,
    AdminUserUpdate,
)
from app.services import user_admin_service as svc

router = APIRouter(prefix="/users", tags=["users"])


def _require_dirigente(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> str:
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )
    role = get_current_user_role(token=token)
    if role != "DIRIGENTE":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ROLE_REQUIRED",
                "message": f"Gestão de usuários restrita a DIRIGENTE (você é {role}).",
            },
        )
    return user_id


def _http_from_admin_error(exc: svc.UserAdminError) -> HTTPException:
    return HTTPException(
        status_code=exc.status,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("", summary="Lista FISCAL + DIRIGENTE (admin)")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_require_dirigente),
) -> AdminUserListResponse:
    items, total = await svc.list_admin_users(db)
    return AdminUserListResponse(items=items, total=total)


@router.get("/{user_id}", summary="Detalhe de um user interno")
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_require_dirigente),
) -> AdminUserRead:
    try:
        return await svc.get_admin_user(db, user_id)
    except svc.UserAdminError as exc:
        raise _http_from_admin_error(exc) from exc


@router.post("", summary="Cria FISCAL ou DIRIGENTE", status_code=201)
async def create_user(
    body: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_require_dirigente),
) -> AdminUserRead:
    try:
        return await svc.create_admin_user(db, body)
    except svc.UserAdminError as exc:
        raise _http_from_admin_error(exc) from exc


@router.patch("/{user_id}", summary="Atualiza user interno (incl. status)")
async def update_user(
    user_id: UUID,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_require_dirigente),
) -> AdminUserRead:
    try:
        return await svc.update_admin_user(db, user_id, body)
    except svc.UserAdminError as exc:
        raise _http_from_admin_error(exc) from exc
