"""SINDESTIVA-PE · Confirmação de presença do TPA (PWA).

DD v1 §3.18.

O TPA, via PWA, confirma que **subiu no navio** (botão "Confirmar
Presença" / "Não vou"). Gera evento que vai pro Fiscal e alimenta
KPI de comparecimento (BI Sprint 7).

`hash_integridade` é anti-fraude: SHA-256(tpa_id + data + confirmou +
timestamp). TPA não pode "confirmar presença" de outro TPA porque o
hash inclui `tpa_id` autenticado.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, Text, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class TpaConfirmacaoPresenca(Base, SoftDeleteMixin):
    """Confirmação de presença do TPA no navio (via PWA)."""

    __tablename__ = "tpa_confirmacoes_presenca"
    __table_args__ = (
        Index("uq_confirm_tpa_data_turno", "tpa_id", "data_referencia", "turno_id", unique=True),
        Index("idx_confirm_tpa_data", "tpa_id", "data_referencia"),
        Index("idx_confirm_hash", "hash_integridade"),
        Index("idx_confirm_deleted_at", "deleted_at",
              postgresql_where=text("deleted_at IS NULL")),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    tpa_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.tpas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lousa_cell_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.lousa_cells.id", ondelete="SET NULL"),
        nullable=True,
    )

    data_referencia: Mapped[date] = mapped_column(Date, nullable=False)
    turno_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.turnos.id", ondelete="RESTRICT"),
        nullable=False,
    )

    confirmou: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confirmado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    # Geo é opt-in (Fase 2 — pedir permissão explicitamente no PWA).
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    precisao_m: Mapped[int | None] = mapped_column(Numeric, nullable=True)
    dispositivo: Mapped[str | None] = mapped_column(Text, nullable=True)

    hash_integridade: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


__all__ = ["TpaConfirmacaoPresenca"]
