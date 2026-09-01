"""SINDESTIVA-PE scraper entrypoint (placeholder Sprint 0)."""
from __future__ import annotations

import structlog

logger = structlog.get_logger()


def main() -> None:
    """Entry point para `sindestiva-scraper`."""
    logger.info("scraper.start", message="SINDESTIVA-PE scraper (placeholder Sprint 0)")


if __name__ == "__main__":
    main()
