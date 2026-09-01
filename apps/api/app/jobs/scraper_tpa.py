"""SINDESTIVA-PE · Job scraper TPA (S2).

Placeholder Sprint 0. Sprint 2 T2-01/T2-02: implementação real
(Playwright + BeautifulSoup + parser tolerante 3 níveis).
"""
from __future__ import annotations

from app.core.logging import get_logger

log = get_logger(__name__)


async def run() -> None:
    """Stub. Sprint 2 implementa."""
    log.info("scraper_tpa.run.placeholder")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
