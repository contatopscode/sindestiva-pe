"""SINDESTIVA-PE · Job purga LGPD 24m (S6 — diário 04:00).

Placeholder Sprint 0. Sprint 6 T6-06: varre `purge_after < now()` em
todas as tabelas e registra cada batch em `lgpd_purge_log`.
"""
from __future__ import annotations

from app.core.logging import get_logger

log = get_logger(__name__)


async def run() -> None:
    """Stub. Sprint 6 implementa."""
    log.info("lgpd_purge.run.placeholder")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
