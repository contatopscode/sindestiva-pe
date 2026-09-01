"""SINDESTIVA-PE · LGPD (termos de consentimento, solicitações Art. 18, purge log).

DD v1 §3.19, §3.23, §3.24.

3 tabelas com **trigger append-only** (UPDATE/DELETE bloqueados):
  - `termos_consentimento`
  - `lgpd_purge_log` (audit do audit)
  - (audit_events e access_log estão em app.models.auditoria)

`lgpd_solicitacoes` é mutável (workflow de status).

TODO(D11): retenção de `termos_consentimento` — indefinida ou 5a
pós-revogação? Recomendação SINDESTIVA Bot = manter **enquanto
houver relação + 5a após exclusão**.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    LgpdStatusEnum,
    LgpdTipoEnum,
    TermoMetodoEnum,
    pg_enum,
)


# ---------------------------------------------------------------------------
# TermoConsentimento (DD v1 §3.19)
# ---------------------------------------------------------------------------

class TermoConsentimento(Base):
    """Registro imutável de cada aceite do termo de consentimento LGPD.

    Base legal do tratamento de dados pessoais. K-5 do plano (parecer
    do advogado). Mesmo se o TPA **recusar** o termo, registramos
    (com `aceito = false`) — recusa é informação importante
    juridicamente.

    Texto do termo vive no S3 (versionado); banco guarda só o hash.
    """

    __tablename__ = "termos_consentimento"
    __table_args__ = (
        Index("idx_termos_tpa_created", "tpa_id", "created_at"),
        Index("idx_termos_versao", "versao_termo"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    tpa_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.tpas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    versao_termo: Mapped[str] = mapped_column(Text, nullable=False)  # v1.0 / v1.1
    aceito: Mapped[bool] = mapped_column(Boolean, nullable=False)
    aceito_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    ip_origem: Mapped[str] = mapped_column(INET, nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)

    metodo: Mapped[TermoMetodoEnum] = mapped_column(
        pg_enum(TermoMetodoEnum), nullable=False
    )
    termo_texto_hash: Mapped[str] = mapped_column(Text(64), nullable=False)
    termo_url_pdf: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# LgpdSolicitacao (DD v1 §3.23)
# ---------------------------------------------------------------------------

class LgpdSolicitacao(Base, TimestampMixin):
    """Workflow de solicitações do titular (Art. 18 LGPD).

    Exclusão (DEFERIDA) dispara job que: 1) anonimiza `tpas`
    (cpf → hash, nome → "TPA EXCLUÍDO"), 2) preserva `audit_events` e
    `remanejamentos` com referência quebrada (`tpa_id` aponta para
    registro anonimizado), 3) registra em `lgpd_purge_log`.

    Retenção: mínima 5a após conclusão (Art. 16 LGPD).
    """

    __tablename__ = "lgpd_solicitacoes"
    __table_args__ = (
        Index("uq_lgpd_protocolo", "protocolo", unique=True),
        Index("idx_lgpd_tpa", "tpa_id"),
        Index("idx_lgpd_tipo", "tipo"),
        Index("idx_lgpd_status", "status"),
        Index("idx_lgpd_prazo", "prazo_resposta"),
        Index("idx_lgpd_purge_after", "purge_after"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    protocolo: Mapped[str] = mapped_column(Text, nullable=False)  # LGPD-2026-0001

    tpa_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.tpas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    tipo: Mapped[LgpdTipoEnum] = mapped_column(
        pg_enum(LgpdTipoEnum), nullable=False
    )
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[LgpdStatusEnum] = mapped_column(
        pg_enum(LgpdStatusEnum),
        nullable=False,
        server_default=text("'RECEBIDA'::lgpd_status_enum"),
    )

    prazo_resposta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recebida_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    respondida_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    executada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resposta_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    documentos_anexos_url: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    responsavel_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    purge_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now() + INTERVAL '5 years'"),
    )


# ---------------------------------------------------------------------------
# LgpdPurgeLog (DD v1 §3.24)
# ---------------------------------------------------------------------------

class LgpdPurgeLog(Base):
    """Log da purga automática 24m (registro imutável).

    Job (T6-06) executa diariamente, lê `purge_after` de **todas** as
    tabelas com esse campo, e deleta em batch. Preserva referência
    histórica (ID + tabela) mesmo após deleção da linha original.

    Retenção: 10 anos (audit do audit — mais que o audit original).
    """

    __tablename__ = "lgpd_purge_log"
    __table_args__ = (
        Index("idx_purge_log_executado", "executado_em"),
        Index("idx_purge_log_tabela", "tabela_origem"),
        Index("idx_purge_log_ids_gin", "registros_ids_antes_delete", postgresql_using="gin"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    executado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    tabela_origem: Mapped[str] = mapped_column(Text, nullable=False)
    registros_deletados: Mapped[int] = mapped_column(Integer, nullable=False)
    criterio: Mapped[str] = mapped_column(Text, nullable=False)  # "purge_after < now()"
    registros_ids_antes_delete: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hash_lote_sha256: Mapped[str] = mapped_column(Text(64), nullable=False)
    job_id: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


__all__ = ["TermoConsentimento", "LgpdSolicitacao", "LgpdPurgeLog"]
