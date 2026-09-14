"""SINDESTIVA-PE · /auditoria (eventos + verificador hash chain)."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_user
from app.core.logging import get_logger
from app.models import AuditEvent
from app.schemas.auditoria import AuditEventRead, VerificarHashChainResponse
from app.services.audit_service import resolver_actor_nome
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
    """Sprint 0: SELECT direto. Sprint 6 T6-01: filtros + paginação cursor.

    HU006 (S1/F4): carrega `actor_user` via `selectinload` para evitar
    LEFT OUTER JOIN monolítico — `User` tem 3 sub-relationships 1:1
    (tpa/fiscal/dirigente) e `selectin` faz 1 round-trip por coleção
    em vez de 1 JOIN por linha. `actor_nome`/`actor_user_email` são
    populados em Python via `resolver_actor_nome`.
    """
    stmt = (
        select(AuditEvent)
        .options(selectinload(AuditEvent.actor_user))
        .order_by(AuditEvent.sequencia.desc())
        .offset(skip)
        .limit(limit)
    )
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    result = await db.execute(stmt)
    events = list(result.scalars().all())

    out: list[AuditEventRead] = []
    for ev in events:
        actor_nome, actor_email = resolver_actor_nome(ev.actor_user)
        item = AuditEventRead.model_validate(ev)
        # model_validate não popula campos não existentes no ORM; set explícito.
        item.actor_nome = actor_nome
        item.actor_user_email = actor_email
        out.append(item)
    return out


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
