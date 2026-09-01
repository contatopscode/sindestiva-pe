"""SINDESTIVA-PE · OGMO notifier (S5 — e-mail + PDF + webhook stub).

Placeholder Sprint 0. Sprint 5 (T5-05, T5-06, T5-07) implementa:
  - Resend como provider (T5-05)
  - WeasyPrint para PDF com hash visível no rodapé (T5-06)
  - Webhook HMAC-SHA256 preparado (T5-07)
  - Retry com backoff 1m/5m/15m (T5-11)
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

log = get_logger(__name__)


class OgmoNotifier:
    """Envia notificações ao OGMO (e-mail primário + webhook stub)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def enviar_email(self, remanejamento_id: str, payload: dict) -> dict:  # noqa: ARG002
        """Stub de envio. Sprint 5 implementa Resend + template."""
        log.info("ogmo.enviar_email.placeholder", remanejamento_id=remanejamento_id)
        return {
            "id": None,
            "canal": "EMAIL",
            "status": "PENDENTE",
            "stub": True,
        }


__all__ = ["OgmoNotifier"]
