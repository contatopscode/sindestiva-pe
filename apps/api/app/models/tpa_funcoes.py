"""SINDESTIVA-PE · Associação N:N TPA ↔ funções (FSW-2026-008)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.catalogos import Funcao
    from app.models.users import Tpa


class TpaFuncao(Base):
    """Funções operacionais de um TPA (além da função base em tpas.funcao_base_id)."""

    __tablename__ = "tpa_funcoes"
    __table_args__ = (
        Index("idx_tpa_funcoes_funcao", "funcao_id"),
        {"schema": "lousa_main"},
    )

    tpa_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.tpas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    funcao_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.funcoes.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    tpa: Mapped["Tpa"] = relationship("Tpa", back_populates="tpa_funcoes_links")
    funcao: Mapped["Funcao"] = relationship("Funcao", lazy="joined")


__all__ = ["TpaFuncao"]
