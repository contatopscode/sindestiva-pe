"""SINDESTIVA-PE · Audit service (S6 — registro de audit_events + LGPD).

Placeholder Sprint 0. Sprint 6 (T6-01, T6-09) implementa:
  - Inserção em audit_events em todo endpoint que toca PII
  - Inserção em access_log via middleware
  - Job diário de verificação do hash chain (T6-03)
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.hash_chain import GENESIS_HASH, compute_hash

log = get_logger(__name__)


class AuditService:
    """Registro de audit_events com hash chain."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def registrar(
        self,
        *,
        entity_type: str,
        entity_id: UUID | None,
        event_type: str,
        actor_user_id: UUID | None,
        actor_role: str | None,
        payload_after: dict[str, Any],
        payload_before: dict[str, Any] | None = None,
        actor_ip: str | None = None,
        actor_user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Stub: calcula hash_evento a partir do último da cadeia. Sprint 6 insere."""
        # TODO Sprint 6: SELECT ultimo hash_anterior, INSERT em audit_events
        hash_evento = compute_hash(GENESIS_HASH, payload_after)
        log.info(
            "audit.registrar.placeholder",
            entity_type=entity_type,
            event_type=event_type,
            hash=hash_evento[:12],
        )
        return {"hash_evento": hash_evento, "stub": True}


__all__ = ["AuditService"]
