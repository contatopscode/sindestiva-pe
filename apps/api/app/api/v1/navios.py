"""SINDESTIVA-PE · /navios (catálogo — cadastro manual pelo Fiscal).

Issue #15: o formulário de cadastro de navios não tinha endpoint de
escrita. Este router expõe o POST com contrato de erro `{code, message}`
igual ao de `/remanejamentos`, para que a UI mostre mensagem específica
(IMO duplicado) em vez de erro genérico.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import get_logger
from app.core.security import get_current_user_id, oauth2_scheme
from app.schemas.navio import NavioCreate, NavioListResponse, NavioRead
from app.services.navio_service import NavioError, criar, listar

router = APIRouter(prefix="/navios", tags=["navios"])
log = get_logger(__name__)


def _user_id_or_401(token: Annotated[str | None, Depends(oauth2_scheme)]) -> str:
    """Helper: garante user autenticado e retorna o id."""
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )
    return user_id


@router.get("", response_model=NavioListResponse, summary="Lista navios (paginado)")
async def list_navios(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_user_id_or_401)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, description="Busca por nome ou IMO"),
) -> NavioListResponse:
    items, total = await listar(db, skip=skip, limit=limit, q=q)
    return NavioListResponse(
        items=[NavioRead.model_validate(n) for n in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=NavioRead, status_code=201, summary="Cadastra navio (issue #15)")
async def create_navio(
    payload: NavioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_user_id_or_401)],
) -> NavioRead:
    """Cria um navio no catálogo.

    - `201` — criado
    - `409` — IMO já cadastrado (`NAVIO_IMO_DUPLICADO`)
    - `422` — payload inválido (validação Pydantic)
    """
    try:
        navio = await criar(
            db,
            nome=payload.nome,
            imo=payload.imo,
            bandeira=payload.bandeira,
            tipo_operacao=payload.tipo_operacao,
        )
    except NavioError as e:
        raise HTTPException(
            status_code=e.status, detail={"code": e.code, "message": e.message}
        ) from e

    return NavioRead.model_validate(navio)
