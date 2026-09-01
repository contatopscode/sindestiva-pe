"""SINDESTIVA-PE · /remanejamentos (CRUD + aprovar)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.core.logging import get_logger
from app.schemas.remanejamento import AprovarRemanejamentoRequest, RemanejamentoCreate
from app.services.remanejamento_service import RemanejamentoService

router = APIRouter(prefix="/remanejamentos", tags=["remanejamentos"])
log = get_logger(__name__)


@router.get("", summary="Lista remanejamentos (paginado)")
async def list_remanejamentos(
    db: AsyncSession = Depends(get_db),  # noqa: ARG001
    _caller: str = Depends(require_user),
    skip: int = 0,
    limit: int = 50,
) -> dict:
    """Sprint 0: stub. Sprint 5 T5-09: SELECT real com filtros."""
    return {"items": [], "total": 0, "skip": skip, "limit": limit}


@router.post("", summary="Cria remanejamento (M5)")
async def create_remanejamento(
    payload: RemanejamentoCreate,
    db: AsyncSession = Depends(get_db),
    caller: str = Depends(require_user),
) -> dict:
    """Sprint 0: stub. Sprint 5 T5-01: implementação real (hash chain)."""
    service = RemanejamentoService(db)
    result = await service.criar(fiscal_id=payload.fiscal_id, payload=payload.model_dump())
    log.info(
        "remanejamento.criar.stub",
        fiscal_id=str(payload.fiscal_id),
        caller=caller,
    )
    return result


@router.patch("/{remanejamento_id}/aprovar", summary="Aprovar remanejamento (M5)")
async def aprovar(
    remanejamento_id: str,
    payload: AprovarRemanejamentoRequest,
    db: AsyncSession = Depends(get_db),  # noqa: ARG001
    _caller: str = Depends(require_user),
) -> dict:
    """Sprint 0: stub. Sprint 5 T5-10: transições controladas."""
    return {
        "id": remanejamento_id,
        "status": "APROVADO",
        "stub": True,
    }
