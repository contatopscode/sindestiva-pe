"""SINDESTIVA-PE · Lousa (snapshots, cells, layout fingerprints).

DD v1 §3.12, §3.13, §3.25.

Risco R1 do plano (OGMO boicota) é mitigado porque `lousa_snapshots`
é a **réplica fiel** da lousa oficial — integração é unilateral.

TODO(D6): normalização de lousa_cells. Decisão D6 = (a) gravar TODAS
+ particionamento mensal. Implementação de partition vai no Sprint 8;
a migration 0001 já prepara a coluna `data_referencia` (denormalizada
para query rápida do BI sem JOIN com lousa_snapshots).
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import CellStatusEnum, SnapshotStatusEnum, pg_enum


# ---------------------------------------------------------------------------
# LousaSnapshot (DD v1 §3.12)
# ---------------------------------------------------------------------------

class LousaSnapshot(Base):
    """Foto da lousa OGMO num instante T.

    Cada scrape (cron 60s durante operação) gera 1 linha. Volume:
    ~57.600 linhas/ano. **Particionada por mês** (Sprint 8 cria
    partições + job mensal) — partition fica fora do MVP (migration
    0001 cria tabela sem partition; Sprint 8 adiciona).

    Soft delete NÃO se aplica — snapshots são imutáveis e particionados.
    """

    __tablename__ = "lousa_snapshots"
    __table_args__ = (
        Index("idx_lousa_snapshots_porto_turno_scraped", "porto_id", "turno_id", "scraped_at"),
        Index("idx_lousa_snapshots_porto_created", "porto_id", "created_at"),
        Index("idx_lousa_snapshots_scraped_at", "scraped_at"),
        Index("idx_lousa_snapshots_html_hash", "html_hash_sha256"),
        Index("idx_lousa_snapshots_layout_fingerprint", "layout_fingerprint_id"),
        Index("idx_lousa_snapshots_status", "status"),
        # FKs são criadas na migration (DD v1 §3.12).
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    porto_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.portos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    turno_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.turnos.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fonte: Mapped[str] = mapped_column(Text, nullable=False)
    # TPA_OGMO / ESCALANET / MANUAL_FISCAL
    url_origem: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_hash_sha256: Mapped[str] = mapped_column(Text(64), nullable=False)

    layout_fingerprint_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.layout_fingerprints.id", ondelete="SET NULL"),
        nullable=True,
    )

    total_celulas: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tpas_escalados: Mapped[int] = mapped_column(Integer, nullable=False)
    duracao_scrape_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[SnapshotStatusEnum] = mapped_column(
        pg_enum(SnapshotStatusEnum),
        nullable=False,
        server_default=text("'OK'::snapshot_status_enum"),
    )
    erro_detalhes: Mapped[str | None] = mapped_column(Text, nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    cells: Mapped[list["LousaCell"]] = relationship(
        "LousaCell",
        back_populates="snapshot",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------------
# LousaCell (DD v1 §3.13)
# ---------------------------------------------------------------------------

class LousaCell(Base):
    """Cada célula da lousa (1.144 × N snapshots).

    Estado atual de cada célula: qual TPA está escalado em qual
    função/faina/turno/porto. **É o que o Centro de Comando renderiza
    em tempo real** (T4-02 do plano).

    LGPD: sim (tpa_id atravessa de `tpas` que tem CPF) — proteções de
    `tpas` se aplicam.
    Retenção: 24m (audit de presença). Sprint 8 adiciona partição.
    """

    __tablename__ = "lousa_cells"
    __table_args__ = (
        Index("uq_lousa_cells_unique", "snapshot_id", "funcao_id", "faina_id", unique=True),
        Index("idx_lousa_cells_porto_turno_data_funcao_faina",
              "porto_id", "turno_id", "data_referencia", "funcao_id", "faina_id"),
        Index("idx_lousa_cells_tpa_data", "tpa_id", "data_referencia"),
        Index("idx_lousa_cells_cais_data", "cais", "data_referencia"),
        Index("idx_lousa_cells_navio", "navio_id"),
        Index("idx_lousa_cells_status", "status_celula"),
        Index("idx_lousa_cells_data", "data_referencia"),
        Index("idx_lousa_cells_snapshot", "snapshot_id"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.lousa_snapshots.id", ondelete="CASCADE"),
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
    funcao_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.funcoes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    faina_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.fainas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cais: Mapped[str | None] = mapped_column(Text, nullable=True)
    navio_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.navios.id", ondelete="SET NULL"),
        nullable=True,
    )
    tpa_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.tpas.id", ondelete="RESTRICT"),
        nullable=True,
    )

    status_celula: Mapped[CellStatusEnum] = mapped_column(
        pg_enum(CellStatusEnum),
        nullable=False,
        server_default=text("'NORMAL'::cell_status_enum"),
    )
    data_referencia: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    snapshot: Mapped[LousaSnapshot] = relationship(
        "LousaSnapshot", back_populates="cells", lazy="joined"
    )


# ---------------------------------------------------------------------------
# LayoutFingerprint (DD v1 §3.25)
# ---------------------------------------------------------------------------

class LayoutFingerprint(Base):
    """Fingerprint do layout OGMO para detectar mudanças (R2 do plano).

    Cada scrape calcula hash da estrutura (não do HTML bruto) e compara
    com último conhecido. Volume esperado: ~50-200 linhas (1 por
    mudança detectada). Apenas 1 `is_current = true` por porto —
    UNIQUE parcial no banco.
    """

    __tablename__ = "layout_fingerprints"
    __table_args__ = (
        Index("uq_fingerprints_porto_versao", "porto_id", "versao", unique=True),
        # UNIQUE parcial: `WHERE is_current = true` (criado na migration).
        Index("idx_fingerprints_seletores_gin", "seletores_parser", postgresql_using="gin"),
        Index("idx_fingerprints_estrutura_gin", "fingerprint_estrutura", postgresql_using="gin"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    porto_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.portos.id", ondelete="RESTRICT"),
        nullable=False,
    )

    versao: Mapped[int] = mapped_column(Integer, nullable=False)
    html_hash_sha256: Mapped[str] = mapped_column(Text(64), nullable=False)

    seletores_parser: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fingerprint_estrutura: Mapped[dict] = mapped_column(JSONB, nullable=False)

    total_snapshots_validados: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    detectado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    substituido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


__all__ = ["LousaSnapshot", "LousaCell", "LayoutFingerprint"]
