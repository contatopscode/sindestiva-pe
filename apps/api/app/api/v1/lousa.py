"""SINDESTIVA-PE · /lousa (read da lousa espelhada)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.core.logging import get_logger
from app.models import LousaAlocacao, Porto, Turno
from app.schemas.lousa import LousaAtualResponse
from app.schemas.scraping import LousaAlocacaoItem, LousaEscalasResponse
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


@router.get(
    "/escalas",
    response_model=LousaEscalasResponse,
    summary="Alocações da lousa por (data, porto, turno) — Sprint 2",
)
async def get_escalas(
    data: str,  # YYYY-MM-DD
    porto: str = "SUAPE",
    turno: str = "DIURNO",
    db: AsyncSession = Depends(get_db),
    _caller: str = Depends(require_user),
) -> LousaEscalasResponse:
    """Retorna alocações (`lousa_alocacao`) para 1 (data, porto, turno).

    Usa a tabela normalizada do Sprint 2 (não o snapshot histórico).
    """
    from datetime import date as _date

    try:
        data_ref = _date.fromisoformat(data)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"`data` deve ser YYYY-MM-DD, recebido {data!r}.",
        ) from exc

    if porto not in {"SUAPE", "RECIFE"}:
        raise HTTPException(
            status_code=422,
            detail=f"`porto` deve ser SUAPE ou RECIFE, recebido {porto!r}.",
        )
    if turno not in {"DIURNO", "NOTURNO"}:
        raise HTTPException(
            status_code=422,
            detail=f"`turno` deve ser DIURNO ou NOTURNO, recebido {turno!r}.",
        )

    # Resolve catálogos.
    porto_row = (await db.execute(select(Porto).where(Porto.codigo == porto))).scalar_one_or_none()
    if porto_row is None:
        raise HTTPException(status_code=404, detail=f"Porto {porto!r} não cadastrado.")
    turno_row = (await db.execute(select(Turno).where(Turno.codigo == turno))).scalar_one_or_none()
    if turno_row is None:
        raise HTTPException(status_code=404, detail=f"Turno {turno!r} não cadastrado.")

    stmt = (
        select(LousaAlocacao)
        .where(
            LousaAlocacao.data_referencia == data_ref,
            LousaAlocacao.porto_id == porto_row.id,
            LousaAlocacao.turno_id == turno_row.id,
        )
        .order_by(LousaAlocacao.faina_id, LousaAlocacao.funcao_id)
    )
    result = await db.execute(stmt)
    alocacoes = list(result.scalars().all())

    return LousaEscalasResponse(
        data=data_ref,
        porto=porto,
        turno=turno,
        total_alocacoes=len(alocacoes),
        alocacoes=[LousaAlocacaoItem.model_validate(a) for a in alocacoes],
    )
