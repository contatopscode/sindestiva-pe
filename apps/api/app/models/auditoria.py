"""SINDESTIVA-PE · Auditoria (audit_events, hash_chain_checkpoint, access_log).

DD v1 §3.20, §3.21, §3.22.

`AuditEvent` é a **tabela mais crítica do sistema** (DD v1). Captura
**toda ação auditável** com hash chain SHA-256. Trigger Postgres
bloqueia UPDATE/DELETE (criado na migration).

`HashChainCheckpoint` registra o resultado de cada execução do job
diário (03:00) que valida a integridade da hash chain.

`AccessLog` rastreia **toda leitura** de dado pessoal (Art. 37 LGPD).
Inserção automática via middleware (T6-09).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# ---------------------------------------------------------------------------
# AuditEvent (DD v1 §3.20)
# ---------------------------------------------------------------------------

class AuditEvent(Base):
    """Log append-only com hash chain (ADR-005).

    Cadeia única global: todos os eventos encadeiam, independente de
    `entity_type`. Adulterar 1 evento quebra a cadeia inteira (mais
    seguro que cadeias paralelas).

    Verificador diário (`hash_chain_checkpoint`) recalcula do início
    e compara — alerta em `#audit-alerts` se quebrar (T6-03).
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("uq_audit_events_sequencia", "sequencia", unique=True),
        Index("uq_audit_events_hash", "hash_evento", unique=True),
        Index("idx_audit_entity", "entity_type"),
        Index("idx_audit_entity_entity_id_created", "entity_type", "entity_id", "criado_em"),
        Index("idx_audit_actor", "actor_user_id"),
        Index("idx_audit_actor_created", "actor_user_id", "criado_em"),
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_event_type_created", "event_type", "criado_em"),
        Index("idx_audit_payload_gin", "payload_after", postgresql_using="gin"),
        Index("idx_audit_criado_em", "criado_em"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    # Sequence: `audit_events_sequencia_seq` (criada na migration).
    sequencia: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)

    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    # remanejamento / lousa_cell / tpa / user / ogmo_notificacao /
    # lgpd_solicitacao / auth
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    # CREATE / UPDATE / DELETE / READ / STATUS_CHANGE / LOGIN / EXPORT

    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    actor_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    actor_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    payload_before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    payload_after: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    hash_anterior: Mapped[str | None] = mapped_column(Text(64), nullable=True)
    hash_evento: Mapped[str] = mapped_column(Text(64), nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# HashChainCheckpoint (DD v1 §3.21)
# ---------------------------------------------------------------------------

class HashChainCheckpoint(Base):
    """Verificador diário (job 03:00) — registra resultado de cada execução.

    MPT/ANTAQ podem ver os últimos N checkpoints e provar que ninguém
    adulterou. Retenção: **indefinida** (prova de integridade histórica).
    """

    __tablename__ = "hash_chain_checkpoint"
    __table_args__ = (
        Index("uq_hash_checkpoint_executado", "executado_em", unique=True),
        Index("idx_hash_checkpoint_integro", "integro"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    executado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    executado_por: Mapped[str] = mapped_column(Text, nullable=False)  # JOB_DIARIO

    total_eventos_verificados: Mapped[int] = mapped_column(BigInteger, nullable=False)
    primeiro_sequencia: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ultimo_sequencia: Mapped[int] = mapped_column(BigInteger, nullable=False)

    hash_calculado_final: Mapped[str] = mapped_column(Text(64), nullable=False)
    hash_esperado_final: Mapped[str] = mapped_column(Text(64), nullable=False)

    integro: Mapped[bool] = mapped_column(Boolean, nullable=False)
    primeiro_evento_com_falha: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    duracao_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    alerta_enviado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# AccessLog (DD v1 §3.22)
# ---------------------------------------------------------------------------

class AccessLog(Base):
    """Log de acesso a dados pessoais (Art. 37 LGPD).

    Rastreabilidade de **toda leitura** de dado pessoal. Inserção
    automática via middleware FastAPI (T6-09). Não tem hash chain
    próprio — eventos vão para `audit_events` (encadeados na cadeia
    global), e `access_log` é a **view materializada** para query
    rápida por TPA.
    """

    __tablename__ = "access_log"
    __table_args__ = (
        Index("idx_access_log_user_created", "user_id", "created_at"),
        Index("idx_access_log_recurso", "recurso_tipo"),
        Index("idx_access_log_recurso_id", "recurso_tipo", "recurso_id"),
        Index("idx_access_log_operacao", "operacao"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    recurso_tipo: Mapped[str] = mapped_column(Text, nullable=False)
    # tpa / remanejamento / lousa_cell / audit_event
    recurso_id: Mapped[UUID] = mapped_column(nullable=False)

    operacao: Mapped[str] = mapped_column(Text, nullable=False)
    # READ / EXPORT_PDF / EXPORT_CSV

    contexto: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_origem: Mapped[str] = mapped_column(INET, nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


__all__ = ["AuditEvent", "HashChainCheckpoint", "AccessLog"]
