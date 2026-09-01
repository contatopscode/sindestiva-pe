"""SINDESTIVA-PE · Remanejamento service (Sprint 5 T5-01/02/03/04).

Cria solicitação de remanejamento (Substituição de TPA) com:
- Hash chain SHA-256 encadeado (DD v1 §3.14)
- AuditEvent imutável (T6-02 pre-work)
- Geração de código SE-YYYYMMDD-NNN via trigger
- Status inicial PENDENTE → APROVADO (após Manoel revisar) → NOTIFICADO_OGMO → ACK
- Disparo assíncrono da notificação ao OGMO (T5-04, SLA 5min)

Decisão D8/D9: a hash chain é **encadeada com `audit_events` global** (não paralela).
Aqui geramos o hash_evento via `compute_hash(previous_hash=audit_ultimo_hash, payload)`.
Remanejamentos sem `hash_evento` próprio — só o `id` é referenciado no audit.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    AuditEvent,
    CctClausula,
    Faina,
    Fiscal,
    Funcao,
    Porto,
    Remanejamento,
    RemanejamentoHistorico,
    StatusRemanejamentoEnum,
    Tpa,
    Turno,
)
from app.services.hash_chain import GENESIS_HASH, compute_hash

log = get_logger(__name__)


class RemanejamentoError(Exception):
    """Erro de domínio. Mensagem voltada pro caller (fiscal/dirigente)."""

    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


async def _ultimo_hash_evento(db: AsyncSession) -> str:
    """Retorna o hash_evento do último AuditEvent, ou GENESIS_HASH."""
    stmt = select(AuditEvent).order_by(AuditEvent.sequencia.desc()).limit(1)
    result = await db.execute(stmt)
    ultimo = result.scalar_one_or_none()
    return ultimo.hash_evento if ultimo else GENESIS_HASH


async def _proximo_sequencia(db: AsyncSession) -> int:
    """Próximo sequencia pra AuditEvent. Usa a sequence do banco."""
    stmt = select(AuditEvent.sequencia).order_by(AuditEvent.sequencia.desc()).limit(1)
    result = await db.execute(stmt)
    ultimo = result.scalar_one_or_none()
    return (ultimo or 0) + 1


async def criar(
    db: AsyncSession,
    *,
    fiscal_id: str,
    tpa_out_id: str,
    tpa_in_id: str | None,
    motivo: str,
    motivo_outro_texto: str | None,
    funcao_origem_id: str,
    faina_origem_id: str,
    porto_id: str,
    turno_id: str,
    data_referencia: date,
    cais_origem: str | None,
    base_legal_cct_id: str | None,
    base_legal_texto_livre: str | None,
    observacoes: str | None,
    anexo_url: str | None,
    snapshot_origem_id: str | None = None,
) -> Remanejamento:
    """Cria remanejamento + AuditEvent + histórico de status.

    Fluxo:
    1. Valida que fiscal existe + TPAs existem + catálogos existem
    2. Gera hash chain (encadeado no audit global)
    3. Cria Remanejamento (status=PENDENTE) + RemanejamentoHistorico
    4. Cria AuditEvent (CREATE, entity_type='remanejamento')
    5. Commit único
    """
    # 1. Validação
    fiscal = (await db.execute(select(Fiscal).where(Fiscal.id == fiscal_id))).scalar_one_or_none()
    if fiscal is None:
        raise RemanejamentoError(404, "FISCAL_NOT_FOUND", f"Fiscal {fiscal_id} não encontrado.")

    tpa_out = (await db.execute(select(Tpa).where(Tpa.id == tpa_out_id))).scalar_one_or_none()
    if tpa_out is None:
        raise RemanejamentoError(404, "TPA_OUT_NOT_FOUND", f"TPA out {tpa_out_id} não encontrado.")

    if tpa_in_id:
        tpa_in = (await db.execute(select(Tpa).where(Tpa.id == tpa_in_id))).scalar_one_or_none()
        if tpa_in is None:
            raise RemanejamentoError(404, "TPA_IN_NOT_FOUND", f"TPA in {tpa_in_id} não encontrado.")

    for cls, id_, name in [
        (Funcao, funcao_origem_id, "funcao"),
        (Faina, faina_origem_id, "faina"),
        (Porto, porto_id, "porto"),
        (Turno, turno_id, "turno"),
    ]:
        found = (await db.execute(select(cls).where(cls.id == id_))).scalar_one_or_none()
        if found is None:
            raise RemanejamentoError(404, f"{name.upper()}_NOT_FOUND", f"{name} {id_} não encontrado.")

    if base_legal_cct_id:
        cl = (await db.execute(select(CctClausula).where(CctClausula.id == base_legal_cct_id))).scalar_one_or_none()
        if cl is None:
            raise RemanejamentoError(404, "CCT_NOT_FOUND", f"CCT {base_legal_cct_id} não encontrada.")

    # 2. Hash chain
    sequencia = await _proximo_sequencia(db)
    hash_anterior = await _ultimo_hash_evento(db)

    # payload canônico do audit (DD v1 §3.20)
    # IMPORTANTE: tudo vira string (UUID, date) antes de ir pro JSONB
    # — asyncpg não serializa UUID nativo.
    agora = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "entity_type": "remanejamento",
        "event_type": "CREATE",
        "actor_user_id": str(fiscal.user_id),
        "actor_role": "FISCAL",
        "fiscal_id": str(fiscal.id),
        "tpa_out_id": str(tpa_out.id),
        "tpa_in_id": str(tpa_in.id) if tpa_in_id else None,
        "motivo": motivo,
        "data_referencia": data_referencia.isoformat(),
        "porto_id": str(porto_id),
        "turno_id": str(turno_id),
        "funcao_origem_id": str(funcao_origem_id),
        "faina_origem_id": str(faina_origem_id),
        "cais_origem": cais_origem,
        "criado_em": agora.isoformat(),
        "sequencia": sequencia,
    }
    hash_evento = compute_hash(hash_anterior, payload)

    # 3. Cria Remanejamento (codigo_se vem do trigger da migration 0001)
    rem = Remanejamento(
        codigo_se="",  # preenchido pelo trigger tg_remanejamentos_codigo_se
        snapshot_origem_id=snapshot_origem_id,
        porto_id=porto_id,
        turno_id=turno_id,
        data_referencia=data_referencia,
        tpa_out_id=tpa_out_id,
        funcao_origem_id=funcao_origem_id,
        faina_origem_id=faina_origem_id,
        cais_origem=cais_origem,
        tpa_in_id=tpa_in_id,
        motivo=motivo,
        motivo_outro_texto=motivo_outro_texto,
        base_legal_cct_id=base_legal_cct_id,
        base_legal_texto_livre=base_legal_texto_livre,
        observacoes=observacoes,
        anexo_url=anexo_url,
        fiscal_id=fiscal.id,
        status=StatusRemanejamentoEnum.PENDENTE,
        ack_at=None,
        ack_por=None,
        nack_motivo=None,
        hash_evento=hash_evento,
        hash_anterior_id=None,
    )
    db.add(rem)
    await db.flush()  # pra ter o id + codigo_se (do trigger)

    # 4. Cria histórico de status (append-only)
    hist = RemanejamentoHistorico(
        remanejamento_id=rem.id,
        status_anterior=None,
        status_novo=StatusRemanejamentoEnum.PENDENTE,
        motivo_transicao="Criação inicial pelo fiscal",
        usuario_id=fiscal.user_id,
        ip_origem=None,
        user_agent=None,
    )
    db.add(hist)

    # 5. Cria AuditEvent (imutável)
    audit = AuditEvent(
        sequencia=sequencia,
        entity_type="remanejamento",
        entity_id=rem.id,
        event_type="CREATE",
        actor_user_id=fiscal.user_id,
        actor_role="FISCAL",
        actor_ip=None,
        actor_user_agent=None,
        payload_before=None,
        payload_after=payload,
        metadata_={"fiscal_id": str(fiscal.id), "codigo_se": rem.codigo_se},
        hash_anterior=hash_anterior,
        hash_evento=hash_evento,
        criado_em=agora,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(rem)

    log.info(
        "remanejamento.criado",
        remanejamento_id=str(rem.id),
        codigo_se=rem.codigo_se,
        fiscal_id=str(fiscal.id),
        tpa_out_id=str(tpa_out.id),
        tpa_in_id=str(tpa_in.id) if tpa_in_id else None,
        hash_evento=hash_evento[:16] + "...",
    )

    return rem


async def aprovar(
    db: AsyncSession,
    *,
    remanejamento_id: str,
    fiscal_id: str,
    observacoes: str | None = None,
) -> Remanejamento:
    """Aprova remanejamento: status PENDENTE → APROVADO."""
    fiscal = (await db.execute(select(Fiscal).where(Fiscal.id == fiscal_id))).scalar_one_or_none()
    if fiscal is None:
        raise RemanejamentoError(404, "FISCAL_NOT_FOUND", f"Fiscal {fiscal_id} não encontrado.")

    rem = (await db.execute(
        select(Remanejamento).where(Remanejamento.id == remanejamento_id)
    )).scalar_one_or_none()
    if rem is None:
        raise RemanejamentoError(404, "REMANEJAMENTO_NOT_FOUND", f"Remanejamento {remanejamento_id} não encontrado.")

    if rem.status != StatusRemanejamentoEnum.PENDENTE:
        raise RemanejamentoError(
            409,
            "INVALID_STATE_TRANSITION",
            f"Status atual {rem.status.value!r} não permite aprovar (esperado PENDENTE).",
        )

    agora = datetime.now(tz=timezone.utc)
    status_anterior = rem.status
    rem.status = StatusRemanejamentoEnum.APROVADO
    if observacoes:
        rem.observacoes = (rem.observacoes or "") + f"\n[APROVAÇÃO] {observacoes}"

    # Histórico
    hist = RemanejamentoHistorico(
        remanejamento_id=rem.id,
        status_anterior=status_anterior,
        status_novo=StatusRemanejamentoEnum.APROVADO,
        motivo_transicao=observacoes or "Aprovação pelo fiscal",
        usuario_id=fiscal.user_id,
        ip_origem=None,
        user_agent=None,
    )
    db.add(hist)

    # Audit (UPDATE) — payload COMPLETO (mesmo usado no hash)
    sequencia = await _proximo_sequencia(db)
    hash_anterior = await _ultimo_hash_evento(db)
    payload = {
        "entity_type": "remanejamento",
        "event_type": "STATUS_CHANGE",
        "actor_user_id": str(fiscal.user_id),
        "actor_role": "FISCAL",
        "remanejamento_id": str(rem.id),
        "status_anterior": status_anterior.value,
        "status_novo": StatusRemanejamentoEnum.APROVADO.value,
        "observacoes": observacoes,
        "criado_em": agora.isoformat(),
        "sequencia": sequencia,
    }
    hash_evento = compute_hash(hash_anterior, payload)
    audit = AuditEvent(
        sequencia=sequencia,
        entity_type="remanejamento",
        entity_id=rem.id,
        event_type="STATUS_CHANGE",
        actor_user_id=fiscal.user_id,
        actor_role="FISCAL",
        actor_ip=None,
        actor_user_agent=None,
        payload_before={"status": status_anterior.value},
        payload_after=payload,  # COMPLETO (mesmo que foi hasheado)
        metadata_={"fiscal_id": str(fiscal.id), "codigo_se": rem.codigo_se},
        hash_anterior=hash_anterior,
        hash_evento=hash_evento,
        criado_em=agora,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(rem)

    log.info("remanejamento.aprovado", remanejamento_id=str(rem.id), fiscal_id=str(fiscal.id))
    return rem


async def listar(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    status_filter: StatusRemanejamentoEnum | None = None,
) -> tuple[list[Remanejamento], int]:
    """Lista remanejamentos com paginacao + filtro opcional por status."""
    stmt = select(Remanejamento)
    if status_filter:
        stmt = stmt.where(Remanejamento.status == status_filter)
    count_stmt = select(Remanejamento.id)
    if status_filter:
        count_stmt = count_stmt.where(Remanejamento.status == status_filter)

    total = len((await db.execute(count_stmt)).scalars().all())
    rows = (await db.execute(
        stmt.order_by(Remanejamento.created_at.desc()).offset(skip).limit(limit)
    )).scalars().all()

    return list(rows), total


__all__ = [
    "RemanejamentoError",
    "criar",
    "aprovar",
    "listar",
]
