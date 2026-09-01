"""SINDESTIVA-PE · Entry point de worker de jobs (placeholder).

Decisão Sprint 0 → Sprint 7 (R45-08): manter APScheduler in-process
vs. worker dedicado (Celery / RQ). Por ora placeholder — Sprint 6
decide baseado em observabilidade do homolog (Manoel Costa).
"""
from __future__ import annotations

import asyncio
from contextlib import suppress

from app.core.logging import configure_logging, get_logger
from app.jobs.hash_chain_verifier import run as hash_chain_run
from app.jobs.lgpd_purge import run as lgpd_purge_run
from app.jobs.scraper_escalanet import run as escalanet_run
from app.jobs.scraper_tpa import run as tpa_run

configure_logging()
log = get_logger("sindestiva.worker")


async def main() -> None:
    """Roda todos os jobs em loop com intervalo (placeholder).

    Sprint 0: 1 execução de cada. Sprint 6: cron-style via APScheduler.
    """
    log.info("worker.startup.placeholder")
    while True:
        with suppress(Exception):
            await tpa_run()
        with suppress(Exception):
            await escalanet_run()
        # Diário — não rodar a cada loop (placeholder só pra ilustrar).
        # await hash_chain_run()
        # await lgpd_purge_run()
        await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("worker.shutdown")
