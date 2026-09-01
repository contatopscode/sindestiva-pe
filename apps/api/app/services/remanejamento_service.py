"""SINDESTIVA-PE · Remanejamento service (S5 — cria evento + hash + dispara notif).

Placeholder Sprint 0. Sprint 5 (T5-01 a T5-10) implementa o ciclo
completo: criação → validação → hash chain → envio OGMO → transição
de status → histórico.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.ogmo_notifier import OgmoNotifier

log = get_logger(__name__)


class RemanejamentoService:
    """Orquestra criação + notificação OGMO."""

    def __init__(self, db: AsyncSession, notifier: OgmoNotifier | None = None) -> None:
        self.db = db
        self.notifier = notifier or OgmoNotifier(db)

    async def criar(self, fiscal_id: UUID, payload: dict) -> dict:  # noqa: ARG002
        """Cria remanejamento. Sprint 0 = placeholder; Sprint 5 = real."""
        log.info("remanejamento.criar.placeholder", fiscal_id=str(fiscal_id))
        return {"id": None, "status": "PENDENTE", "stub": True}


__all__ = ["RemanejamentoService"]
