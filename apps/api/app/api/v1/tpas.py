"""SINDESTIVA-PE · /tpas (CRUD admin FISCAL + DIRIGENTE)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import get_current_user_id, get_current_user_role, oauth2_scheme
from app.models.enums import TpaStatusEnum
from app.schemas.tpa_admin import (
    AdminTpaCreate,
    AdminTpaFuncaoMeta,
    AdminTpaListResponse,
    AdminTpaRead,
    AdminTpaUpdate,
)
from app.services import tpa_admin_service as svc

router = APIRouter(prefix="/tpas", tags=["tpas"])

_TPAS_ADMIN_ROLES = frozenset({"FISCAL", "DIRIGENTE"})


def _require_fiscal_or_dirigente(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> str:
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )
    role = get_current_user_role(token=token)
    if role not in _TPAS_ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ROLE_REQUIRED",
                "message": (
                    f"Cadastro de TPAs restrito a FISCAL ou DIRIGENTE (você é {role})."
                ),
            },
        )
    return user_id


def _http_from_admin_error(exc: svc.TpaAdminError) -> HTTPException:
    return HTTPException(
        status_code=exc.status,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/meta/funcoes", summary="Catálogo de funções (dropdown admin)")
async def list_funcoes_meta(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_require_fiscal_or_dirigente),
) -> list[AdminTpaFuncaoMeta]:
    return await svc.list_tpa_funcoes(db)


@router.get("", summary="Lista TPAs (admin)")
async def list_tpas(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_require_fiscal_or_dirigente),
    q: str | None = Query(default=None, max_length=120),
    status_cadastro: TpaStatusEnum | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminTpaListResponse:
    items, total = await svc.list_admin_tpas(
        db,
        q=q,
        status_cadastro=status_cadastro,
        page=page,
        page_size=page_size,
    )
    return AdminTpaListResponse(items=items, total=total)


@router.get("/{tpa_id}", summary="Detalhe de um TPA")
async def get_tpa(
    tpa_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_require_fiscal_or_dirigente),
) -> AdminTpaRead:
    try:
        return await svc.get_admin_tpa(db, tpa_id)
    except svc.TpaAdminError as exc:
        raise _http_from_admin_error(exc) from exc


@router.post("", summary="Cria TPA + User(role=TPA)", status_code=201)
async def create_tpa(
    body: AdminTpaCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_require_fiscal_or_dirigente),
) -> AdminTpaRead:
    try:
        return await svc.create_admin_tpa(db, body)
    except svc.TpaAdminError as exc:
        raise _http_from_admin_error(exc) from exc


@router.patch("/{tpa_id}", summary="Atualiza cadastro TPA")
async def update_tpa(
    tpa_id: UUID,
    body: AdminTpaUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_require_fiscal_or_dirigente),
) -> AdminTpaRead:
    try:
        return await svc.update_admin_tpa(db, tpa_id, body)
    except svc.TpaAdminError as exc:
        raise _http_from_admin_error(exc) from exc
