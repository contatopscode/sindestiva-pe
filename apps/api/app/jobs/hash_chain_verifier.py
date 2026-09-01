"""SINDESTIVA-PE · Job verificador de hash chain (S6 — diário 03:00).

Placeholder Sprint 0. Sprint 6 T6-03: implementa varredura completa
e grava em `hash_chain_checkpoint`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.database import session_scope
from app.core.logging import get_logger
from app.models import AuditEvent
from app.services.hash_chain import verify_chain
from sqlalchemy import select

log = get_logger(__name__)


async def run() -> None:
    """Stub Sprint 0. Sprint 6: SELECT + verify + INSERT checkpoint + alerta."""
    async with session_scope() as db:
        stmt = select(AuditEvent).order_by(AuditEvent.sequencia)
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        integro, idx = verify_chain(events)
        log.info(
            "hash_chain_verifier.run.placeholder",
            total=len(events),
            integro=integro,
            idx_falha=idx,
            ts=datetime.now(tz=timezone.utc).isoformat(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
