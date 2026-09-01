"""SINDESTIVA-PE · Scraping da lousa (origem bruta + alocação normalizada).

Sprint 2 (S2 — 22/set a 05/out).

Decisão arquitetural (P2 do plano v1.0): o scraping persiste em DUAS
tabelas pra permitir reprocesso sem re-raspar a internet:

  1. `lousa_escala_origem` (DD v1 §3.27 — Sprint 2 adiciona)
     - Payload bruto + hash SHA-256 do conteúdo
     - 1 linha por (fonte, porto, turno, data_referencia)
     - UNIQUE (fonte, porto_id, turno_id, data_referencia) garante
       idempotência: re-scrape do mesmo dia não duplica.
     - Se `content_hash` muda entre scrapes do mesmo dia, detectamos
       mudança na fonte (R2 do plano — TPA muda layout).

  2. `lousa_alocacao` (DD v1 §3.28 — Sprint 2 adiciona)
     - Resultado normalizado em 1.144 células/dia esperadas
       (26 funções × 11 fainas × 2 turnos × 2 portos).
     - Cada linha = 1 célula (funcao × faina) num turno/porto/data.
     - FK para `lousa_escala_origem` (cascade) + `portos` + `turnos`
       + `fainas` + `funcoes`.
     - LGPD: NÃO referenciamos `tpas.id` direto — persistimos
       `trabalhador_matricula` (chave funcional OGMO) e mantemos
       `trabalhador_id` (FK) NULLABLE. Reconciliação TPA ↔ escala é
       um job batch (Sprint 5 K-5) com termo de consentimento já
       aceito via PWA (Sprint 1).

`fk_mando`, `fk_terno`, `fk_tecnica`, `fk_vigia` são flags
(0/1) que indicam a qual categoria pertence a função escalada
naquela célula. Permitem KPIs rápidos tipo "TPAs de Mando
escalados em 2026-09-15" sem JOIN com `funcoes`.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CHAR,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import FonteEscalaEnum, StatusScrapingEnum, pg_enum

# ---------------------------------------------------------------------------
# LousaEscalaOrigem (DD v1 §3.27)
# ---------------------------------------------------------------------------

class LousaEscalaOrigem(Base):
    """Payload bruto do scrape, com hash pra detectar mudança de layout.

    Volume: ~1-2 linhas/dia (1 por fonte × porto). 730-1460 linhas/ano.
    Retenção: 24m (audit + reprocesso). Sem soft delete — é imutável.
    """

    __tablename__ = "lousa_escala_origem"
    __table_args__ = (
        UniqueConstraint(
            "fonte", "porto_id", "turno_id", "data_referencia",
            name="uq_escala_origem_fonte_porto_turno_data",
        ),
        Index("idx_escala_origem_data", "data_referencia"),
        Index("idx_escala_origem_fonte", "fonte"),
        Index("idx_escala_origem_status", "status"),
        Index("idx_escala_origem_content_hash", "content_hash"),
        Index(
            "idx_escala_origem_payload_gin",
            "payload_jsonb",
            postgresql_using="gin",
        ),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    fonte: Mapped[FonteEscalaEnum] = mapped_column(
        pg_enum(FonteEscalaEnum), nullable=False
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
    url_origem: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    payload_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False)

    duracao_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[StatusScrapingEnum] = mapped_column(
        pg_enum(StatusScrapingEnum),
        nullable=False,
        server_default=text("'SUCESSO'::status_scraping_enum"),
    )
    erro_detalhes: Mapped[str | None] = mapped_column(Text, nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# LousaAlocacao (DD v1 §3.28)
# ---------------------------------------------------------------------------

class LousaAlocacao(Base):
    """Célula normalizada da lousa (1 linha por função × faina × turno × porto × data).

    Volume esperado:
      26 funções × 11 fainas × 2 turnos × 2 portos = 1.144 células/dia
      × 365 dias = ~417.560 linhas/ano. Sem soft delete — append-only
      com FK CASCADE para `lousa_escala_origem`.

    LGPD: `trabalhador_matricula` é a chave funcional OGMO (não é dado
    pessoal sensível por si só — é um número de cadastro público).
    `trabalhador_id` (FK → `tpas.id`) é NULLABLE e populado apenas
    após reconciliação batch (Sprint 5 K-5) com termo já aceito.
    """

    __tablename__ = "lousa_alocacao"
    __table_args__ = (
        UniqueConstraint(
            "escala_origem_id", "faina_id", "funcao_id",
            name="uq_alocacao_origem_faina_funcao",
        ),
        Index("idx_alocacao_data_porto_turno", "data_referencia", "porto_id", "turno_id"),
        Index("idx_alocacao_faina", "faina_id"),
        Index("idx_alocacao_funcao", "funcao_id"),
        Index("idx_alocacao_trabalhador_matricula", "trabalhador_matricula"),
        Index("idx_alocacao_trabalhador_id", "trabalhador_id"),
        Index("idx_alocacao_escala_origem", "escala_origem_id"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    escala_origem_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.lousa_escala_origem.id", ondelete="CASCADE"),
        nullable=False,
    )
    porto_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.portos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    turno_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.turnos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    faina_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.fainas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    funcao_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.funcoes.id", ondelete="RESTRICT"),
        nullable=False,
    )

    data_referencia: Mapped[date] = mapped_column(Date, nullable=False)

    # Identificação funcional do TPA (LGPD-safe: matrícula OGMO é nº público).
    trabalhador_matricula: Mapped[str | None] = mapped_column(Text, nullable=True)
    # FK opcional para `tpas` — populada por job de reconciliação Sprint 5.
    trabalhador_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.tpas.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Flags por categoria (DD v1 §3.8: MANDO/TERNO/TECNICA/VIGIA).
    # 1 se a função escalada pertence àquela categoria, NULL caso contrário.
    fk_mando: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fk_terno: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fk_tecnica: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fk_vigia: Mapped[int | None] = mapped_column(Integer, nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


__all__ = ["LousaAlocacao", "LousaEscalaOrigem"]
