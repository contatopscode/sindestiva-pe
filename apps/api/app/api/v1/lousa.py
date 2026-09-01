"""SINDESTIVA-PE · /lousa (read da lousa espelhada)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.core.logging import get_logger
from app.schemas.lousa import LousaAtualResponse
from app.services.lousa_service import LousaService

router = APIRouter(prefix="/lousa", tags=["lousa"])
log = get_logger(__name__)


@router.get("/atual", response_model=LousaAtualResponse, summary="Snapshot mais recente")
async def get_atual(
    porto: str = "SUAPE",
    turno: str = "DIURNO",
    db: AsyncSession = Depends(get_db),
    _caller: str = Depends(require_user),
) -> LousaAtualResponse:
    """Retorna o último snapshot (Sprint 0: pode ser None se DB vazio)."""
    service = LousaService(db)
    snapshot = await service.get_current_snapshot(porto_slug=porto, turno_codigo=turno)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum snapshot para porto={porto} turno={turno} (DB vazio).",
        )
    return LousaAtualResponse(
        snapshot=snapshot,  # type: ignore[arg-type]
        total_tpas=snapshot.total_tpas_escalados,
        total_celulas_ocupadas=snapshot.total_tpas_escalados,
    )


@router.get("/porto/{porto_slug}/turno/{turno_codigo}", summary="Snapshot por (porto, turno)")
async def get_por_porto_turno(
    porto_slug: str,
    turno_codigo: str,
    db: AsyncSession = Depends(get_db),
    _caller: str = Depends(require_user),
) -> dict:
    """Sprint 0: mesmo que /atual mas com path params explícitos."""
    service = LousaService(db)
    snapshot = await service.get_current_snapshot(
        porto_slug=porto_slug, turno_codigo=turno_codigo
    )
    if snapshot is None:
        return {"snapshot": None, "stub": True}
    return {"snapshot_id": str(snapshot.id), "status": snapshot.status.value}
