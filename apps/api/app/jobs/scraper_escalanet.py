"""SINDESTIVA-PE · Job scraper EscalaNet (S2 — Recife).

Placeholder Sprint 0. Sprint 2 T2-04: implementação real (HTTPX).
"""
from __future__ import annotations

from app.core.logging import get_logger

log = get_logger(__name__)


async def run() -> None:
    """Stub. Sprint 2 implementa."""
    log.info("scraper_escalanet.run.placeholder")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
