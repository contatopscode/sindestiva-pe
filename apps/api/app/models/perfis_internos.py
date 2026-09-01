"""SINDESTIVA-PE · Perfis de Fiscal e Dirigente.

DD v1 §3.4 (fiscais) e §3.5 (dirigentes).

Manoel Costa é o fiscal-piloto de Suape (cerca de 10 fiscais totais).
Josias Martins Santiago é o Dirigente principal (DPO = Paulo).

Decisão D2: retenção de Fiscais/Dirigentes = 5a ou 24m?
Recomendação SINDESTIVA Bot = 5a para fiscais (audit fiscal/legal),
24m para dirigentes (igual TPA).
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import FiscalStatusEnum, pg_enum


# ---------------------------------------------------------------------------
# Fiscal (DD v1 §3.4)
# ---------------------------------------------------------------------------

class Fiscal(Base, TimestampMixin, SoftDeleteMixin):
    """Perfil de negócio do Fiscal (1:1 com User onde role=FISCAL).

    Volume esperado: ~10 linhas (Suape 7 + Recife 3).
    Retenção: 5a (audit fiscal/legal — D2).
    """

    __tablename__ = "fiscais"
    __table_args__ = (
        Index("uq_fiscais_user_id", "user_id", unique=True),
        Index("uq_fiscais_cpf", "cpf", unique=True),
        Index("uq_fiscais_matricula_sindicato", "matricula_sindicato", unique=True),
        Index("idx_fiscais_nome_trgm", "nome_completo", postgresql_using="gin",
              postgresql_ops={"nome_completo": "gin_trgm_ops"}),
        Index("idx_fiscais_porto", "porto_id"),
        Index("idx_fiscais_status", "status"),
        Index("idx_fiscais_deleted_at", "deleted_at",
              postgresql_where=text("deleted_at IS NULL")),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    cpf: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    nome_completo: Mapped[str] = mapped_column(Text, nullable=False)
    matricula_sindicato: Mapped[str] = mapped_column(Text, nullable=False)
    telefone: Mapped[str] = mapped_column(Text, nullable=False)

    porto_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.portos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    turno_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.turnos.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[FiscalStatusEnum] = mapped_column(
        pg_enum(FiscalStatusEnum),
        nullable=False,
        server_default=text("'ATIVO'::fiscal_status_enum"),
    )

    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)

    aprovador_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    user: Mapped[object] = relationship("User", back_populates="fiscal", lazy="joined")

    # Retenção específica: 5 anos (D2) — sobrescreve o default do mixin
    # (que é 24m). O DDL da migration 0001 já reflete isso via
    # `server_default=now() + INTERVAL '5 years'`. Aqui só ajustamos
    # a metadata do SQLAlchemy para alinhar.
    purge_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now() + INTERVAL '5 years'"),
    )


# ---------------------------------------------------------------------------
# Dirigente (DD v1 §3.5)
# ---------------------------------------------------------------------------

class Dirigente(Base, TimestampMixin, SoftDeleteMixin):
    """Perfil de Dirigente (Josias, diretores) — 1:1 com User onde role=DIRIGENTE.

    Volume esperado: ~5-10 linhas.
    Apenas 1 user pode ter `is_dpo = true` (Paulo é o DPO) — CHECK
    aplicado via trigger (DD v1 §3.5).
    """

    __tablename__ = "dirigentes"
    __table_args__ = (
        Index("uq_dirigentes_user_id", "user_id", unique=True),
        Index("uq_dirigentes_cpf", "cpf", unique=True),
        Index("uq_dirigentes_matricula", "matricula_sindicato", unique=True),
        Index("idx_dirigentes_deleted_at", "deleted_at",
              postgresql_where=text("deleted_at IS NULL")),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    cpf: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    nome_completo: Mapped[str] = mapped_column(Text, nullable=False)
    cargo: Mapped[str] = mapped_column(Text, nullable=False)
    matricula_sindicato: Mapped[str] = mapped_column(Text, nullable=False)

    is_dpo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    data_inicio_mandato: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim_mandato: Mapped[date | None] = mapped_column(Date, nullable=True)

    user: Mapped[object] = relationship("User", back_populates="dirigente", lazy="joined")


__all__ = ["Fiscal", "Dirigente"]
