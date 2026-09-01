"""SINDESTIVA-PE · Catálogos (portos, turnos, funções, fainas, navios, CCT, feriados).

DD v1 §3.6 a §3.11, §3.26.

São as 5 tabelas de seed do Sprint 1 (T1-03 do plano). Volume baixo,
sem soft delete (são imutáveis em produção), sem hash chain.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, Time, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


# ---------------------------------------------------------------------------
# Porto (DD v1 §3.6)
# ---------------------------------------------------------------------------

class Porto(Base, TimestampMixin):
    """Portos operados pelo Sindicato (SUAPE, RECIFE). Catálogo imutável."""

    __tablename__ = "portos"
    __table_args__ = (
        Index("uq_portos_codigo", "codigo", unique=True),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    codigo: Mapped[str] = mapped_column(Text, nullable=False)  # SUAPE / RECIFE
    nome_completo: Mapped[str] = mapped_column(Text, nullable=False)
    cnpj_ogmo: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_tpa: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_escalanet: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


# ---------------------------------------------------------------------------
# Turno (DD v1 §3.7)
# ---------------------------------------------------------------------------

class Turno(Base):
    """Turnos de operação portuária. Catálogo imutável.

    Decisão D4: turno intermediário (16-20, 04-08)? Manoel confirma.
    Por ora seed com 2 turnos.
    """

    __tablename__ = "turnos"
    __table_args__ = (
        Index("uq_turnos_codigo", "codigo", unique=True),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    codigo: Mapped[str] = mapped_column(Text, nullable=False)  # DIURNO / NOTURNO
    nome_exibicao: Mapped[str] = mapped_column(Text, nullable=False)
    hora_inicio: Mapped[Time] = mapped_column(Time, nullable=False)  # type: ignore[valid-type]
    hora_fim: Mapped[Time] = mapped_column(Time, nullable=False)  # type: ignore[valid-type]
    duracao_horas: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# Funcao (DD v1 §3.8)
# ---------------------------------------------------------------------------

class Funcao(Base):
    """As 26 funções da lousa oficial (Mando 6 + Terno 6 + Técnica 12 + Vigia 2).

    Decisão D5: lista oficial das 26 funções. Técnico = 12 (Sinaleiro,
    Guincho A, Guincho B, Emp. GP, Emp. PP, V. Pesado, V. Leve,
    Manobrista, Transp., Pá Mec. + 2 a definir com Manoel).
    """

    __tablename__ = "funcoes"
    __table_args__ = (
        Index("uq_funcoes_codigo", "codigo", unique=True),
        Index("uq_funcoes_ordem", "ordem_lousa", unique=True),
        Index("idx_funcoes_categoria", "categoria"),
        Index("idx_funcoes_nome_trgm", "nome_exibicao", postgresql_using="gin",
              postgresql_ops={"nome_exibicao": "gin_trgm_ops"}),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    codigo: Mapped[str] = mapped_column(Text, nullable=False)
    nome_exibicao: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[str] = mapped_column(Text, nullable=False)  # MANDO / TERNO / TECNICA / VIGIA
    ordem_lousa: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# Faina (DD v1 §3.9)
# ---------------------------------------------------------------------------

class Faina(Base):
    """As 10 linhas da lousa (Produção, Salário, Sacaria, etc.).

    Decisão D5: protótipo lista 8 por nome mas diz 10 — Manoel confirma.
    """

    __tablename__ = "fainas"
    __table_args__ = (
        Index("uq_fainas_codigo", "codigo", unique=True),
        Index("uq_fainas_ordem", "ordem_lousa", unique=True),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    codigo: Mapped[str] = mapped_column(Text, nullable=False)
    nome_exibicao: Mapped[str] = mapped_column(Text, nullable=False)
    cor_hex: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordem_lousa: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# Navio (DD v1 §3.10)
# ---------------------------------------------------------------------------

class Navio(Base):
    """Navios referenciados em BI e em observações de remanejamento.

    Não é scrape — pode ser inserido manualmente pelo Fiscal ou
    importado em Sprint futuro. Volume esperado: ~100-500/ano.
    """

    __tablename__ = "navios"
    __table_args__ = (
        Index("uq_navios_imo", "imo", unique=True),
        Index("idx_navios_nome_trgm", "nome", postgresql_using="gin",
              postgresql_ops={"nome": "gin_trgm_ops"}),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    imo: Mapped[str | None] = mapped_column(Text, nullable=True)
    bandeira: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_operacao: Mapped[str | None] = mapped_column(Text, nullable=True)  # RO_RO / CONTAINER / ...
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# CctClausula (DD v1 §3.11)
# ---------------------------------------------------------------------------

class CctClausula(Base):
    """Cláusulas da CCT 2024-2026 (e futuras) que fundamentam motivos
    de remanejamento. Base legal exibida no modal e no PDF.

    Seed Sprint 1 vazio; populado no Sprint 0 K-2 (Josias entrega CCT
    digitalizada) e Sprint 5 T5-03. Atualização é evento crítico: cria
    nova versão, marca anterior `is_active = false`, **nunca apaga**.
    """

    __tablename__ = "cct_clausulas"
    __table_args__ = (
        Index("uq_cct_versao_clausula", "versao_cct", "clausula", unique=True),
        Index("idx_cct_versao", "versao_cct"),
        Index("idx_cct_motivos_gin", "motivos_vinculados", postgresql_using="gin"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    versao_cct: Mapped[str] = mapped_column(Text, nullable=False)  # 2024-2026
    clausula: Mapped[str] = mapped_column(Text, nullable=False)  # "cl. 12ª, §3º"
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    motivos_vinculados: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# FeriadoNacional (DD v1 §3.26)
# ---------------------------------------------------------------------------

class FeriadoNacional(Base):
    """Calendário auxiliar para antecipar envio de e-mail ao OGMO se
    o remanejamento cair em véspera de feriado / fim de semana.

    Volume: ~15-20 linhas (atualizado anualmente).
    """

    __tablename__ = "feriados_nacionais"
    __table_args__ = (
        Index("uq_feriados_data", "data", unique=True),
        Index("idx_feriados_tipo", "tipo"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    data: Mapped[date] = mapped_column(Date, nullable=False)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    # NACIONAL / ESTADUAL_PE / MUNICIPAL_SUAPE / MUNICIPAL_RECIFE
    is_recorrente: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


__all__ = [
    "Porto",
    "Turno",
    "Funcao",
    "Faina",
    "Navio",
    "CctClausula",
    "FeriadoNacional",
]
