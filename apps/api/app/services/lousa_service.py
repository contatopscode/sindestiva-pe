"""SINDESTIVA-PE · Lousa service (S4 — orquestra snapshot + cells).

Placeholder Sprint 0. Sprint 2 (T2-01) implementa o scraper; Sprint 4
(T4-02) implementa a query otimizada para o Centro de Comando.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import LousaCell, LousaSnapshot, Porto, Turno

log = get_logger(__name__)


class LousaService:
    """Operações de leitura sobre snapshots + cells."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_current_snapshot(
        self,
        *,
        porto_slug: str,
        turno_codigo: str,
    ) -> LousaSnapshot | None:
        """Retorna o snapshot mais recente para (porto, turno)."""
        stmt = (
            select(LousaSnapshot)
            .join(Porto, Porto.id == LousaSnapshot.porto_id)
            .join(Turno, Turno.id == LousaSnapshot.turno_id)
            .where(Porto.codigo == porto_slug, Turno.codigo == turno_codigo)
            .order_by(LousaSnapshot.scraped_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_cells(self, snapshot_id: UUID) -> list[LousaCell]:
        """Retorna todas as cells de um snapshot."""
        stmt = select(LousaCell).where(LousaCell.snapshot_id == snapshot_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


__all__ = ["LousaService"]
