"""SINDESTIVA-PE · /auditoria (eventos + verificador hash chain)."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.core.logging import get_logger
from app.models import AuditEvent
from app.schemas.auditoria import AuditEventRead, VerificarHashChainResponse
from app.services.hash_chain import verify_chain

router = APIRouter(prefix="/auditoria", tags=["auditoria"])
log = get_logger(__name__)


@router.get("/eventos", response_model=list[AuditEventRead], summary="Lista audit events")
async def list_eventos(
    db: AsyncSession = Depends(get_db),
    _caller: str = Depends(require_user),
    entity_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AuditEventRead]:
    """Sprint 0: SELECT direto. Sprint 6 T6-01: filtros + paginação cursor."""
    stmt = select(AuditEvent).order_by(AuditEvent.sequencia.desc()).offset(skip).limit(limit)
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    result = await db.execute(stmt)
    events = list(result.scalars().all())
    return [AuditEventRead.model_validate(e) for e in events]


@router.post(
    "/verificar-hash-chain",
    response_model=VerificarHashChainResponse,
    summary="Verifica integridade do hash chain",
)
async def verificar_hash_chain(
    db: AsyncSession = Depends(get_db),
    _caller: str = Depends(require_user),
) -> VerificarHashChainResponse:
    """Roda `verify_chain` sobre `audit_events` ordenado por sequência.

    Sprint 0: varre todos (dev). Sprint 6 T6-03: varre apenas últimos 50k
    (janela 24h) + grava `hash_chain_checkpoint`.
    """
    started = datetime.now(tz=timezone.utc)
    stmt = select(AuditEvent).order_by(AuditEvent.sequencia)
    result = await db.execute(stmt)
    events = list(result.scalars().all())
    integro, idx_falha = verify_chain(events)
    duracao_ms = int((datetime.now(tz=timezone.utc) - started).total_seconds() * 1000)
    log.info(
        "auditoria.verificar",
        total=len(events),
        integro=integro,
        idx_falha=idx_falha,
        duracao_ms=duracao_ms,
    )
    return VerificarHashChainResponse(
        integro=integro,
        total_eventos=len(events),
        primeiro_evento_com_falha=idx_falha if not integro else None,
        duracao_ms=duracao_ms,
        executado_em=datetime.now(tz=timezone.utc),
    )
