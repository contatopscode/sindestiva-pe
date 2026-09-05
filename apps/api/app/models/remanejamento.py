"""SINDESTIVA-PE · Remanejamento (cabeçalho + histórico).

DD v1 §3.14, §3.15.

`Remanejamento` é o "coração" do sistema (DD v1) — Manoel clica na
lousa, preenche o modal (motivo + base legal), e gera 1 remanejamento
que vira e-mail pro OGMO. SLA de 5 min (T5-04) entre criação e
notificação.

TODO(D8): hash chain de `remanejamentos` é encadeada com `audit_events`
ou paralela? Recomendação SINDESTIVA Bot = (a) cadeia única global
em `audit_events`; `remanejamentos.hash_evento` vira redundante.
Mantemos a coluna na migration 0001 (DD v1 manda) e marcamos
`hash_evento` como deprecado em revisão futura.

TODO(D9): `remanejamento_historico` × `audit_events` — manter 2 ou
unificar? Recomendação = unificar em `audit_events` e criar view
`vw_remanejamento_historico`. Migration 0001 mantém as 2 tabelas
(seguindo o DD); unificação fica para migration 0002 pós-Sprint 6.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Text, String, text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import MotivoRemanejamentoEnum, StatusRemanejamentoEnum, pg_enum


# ---------------------------------------------------------------------------
# Remanejamento (DD v1 §3.14)
# ---------------------------------------------------------------------------

class Remanejamento(Base, TimestampMixin, SoftDeleteMixin):
    """Solicitação de substituição de TPA. Cabeçalho do ciclo de vida.

    `codigo_se` é o ID visível no protótipo (`SE-2026-0812-014`);
    gerado por trigger BEFORE INSERT (`SE-` + `YYYYMMDD-` + sequencial
    diário).

    Retenção: 5 anos (audit legal/trabalhista — Art. 7º LGPD + CLT
    art. 11).
    """

    __tablename__ = "remanejamentos"
    __table_args__ = (
        Index("uq_remanejamentos_codigo_se", "codigo_se", unique=True),
        Index("idx_remanejamentos_snapshot", "snapshot_origem_id"),
        Index("idx_remanejamentos_data", "data_referencia"),
        Index("idx_remanejamentos_tpa_out", "tpa_out_id"),
        Index("idx_remanejamentos_tpa_in", "tpa_in_id"),
        Index("idx_remanejamentos_motivo", "motivo"),
        Index("idx_remanejamentos_cct", "base_legal_cct_id"),
        Index("idx_remanejamentos_fiscal", "fiscal_id"),
        Index("idx_remanejamentos_status", "status"),
        Index("idx_remanejamentos_hash", "hash_evento"),
        Index("idx_remanejamentos_hash_anterior", "hash_anterior_id"),
        Index("idx_remanejamentos_created", "created_at"),
        Index("idx_remanejamentos_purge_after", "purge_after"),
        Index("idx_remanejamentos_deleted_at", "deleted_at",
              postgresql_where=text("deleted_at IS NULL")),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    codigo_se: Mapped[str] = mapped_column(Text, nullable=False)  # SE-YYYYMMDD-NNN

    snapshot_origem_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.lousa_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
    )
    porto_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.portos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    turno_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.turnos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    data_referencia: Mapped[date] = mapped_column(Date, nullable=False)

    tpa_out_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.tpas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    funcao_origem_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.funcoes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    faina_origem_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.fainas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cais_origem: Mapped[str | None] = mapped_column(Text, nullable=True)

    tpa_in_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.tpas.id", ondelete="RESTRICT"),
        nullable=True,
    )

    motivo: Mapped[MotivoRemanejamentoEnum] = mapped_column(
        pg_enum(MotivoRemanejamentoEnum), nullable=False
    )
    motivo_outro_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_legal_cct_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.cct_clausulas.id", ondelete="RESTRICT"),
        nullable=True,
    )
    base_legal_texto_livre: Mapped[str | None] = mapped_column(Text, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    anexo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    fiscal_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.fiscais.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[StatusRemanejamentoEnum] = mapped_column(
        pg_enum(StatusRemanejamentoEnum),
        nullable=False,
        server_default=text("'PENDENTE'::status_remanejamento_enum"),
    )
    ack_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ack_por: Mapped[str | None] = mapped_column(Text, nullable=True)
    nack_motivo: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Hash chain (DD v1 §3.14) — ver TODO(D8) sobre unificação.
    hash_evento: Mapped[str] = mapped_column(String(64), nullable=False)
    hash_anterior_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.remanejamentos.id", ondelete="SET NULL"),
        nullable=True,
    )


# ---------------------------------------------------------------------------
# RemanejamentoHistorico (DD v1 §3.15)
# ---------------------------------------------------------------------------

class RemanejamentoHistorico(Base):
    """Append-only do ciclo de vida do remanejamento. Alimenta a tela
    `/remanejamentos` (T5-09) e o export PDF.

    Trigger BEFORE UPDATE/DELETE bloqueia (imutável) — criado na
    migration. Sem `TimestampMixin`/`SoftDeleteMixin` porque é
    imutável e tem só `created_at`.
    """

    __tablename__ = "remanejamento_historico"
    __table_args__ = (
        Index("idx_reman_hist_remanejamento_created", "remanejamento_id", "created_at"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    remanejamento_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.remanejamentos.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status_anterior: Mapped[StatusRemanejamentoEnum | None] = mapped_column(
        pg_enum(StatusRemanejamentoEnum),
        nullable=True,
    )
    status_novo: Mapped[StatusRemanejamentoEnum] = mapped_column(
        pg_enum(StatusRemanejamentoEnum), nullable=False
    )

    motivo_transicao: Mapped[str | None] = mapped_column(Text, nullable=True)

    usuario_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    ip_origem: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


__all__ = ["Remanejamento", "RemanejamentoHistorico"]
