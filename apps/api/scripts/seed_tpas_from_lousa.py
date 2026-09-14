"""SINDESTIVA-PE · Backfill TPAs a partir de matrículas na lousa (homolog).

Idempotente em `matricula_ogmo`. Requer `ALLOW_TPA_STUB=1` no ambiente.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import session_scope  # noqa: E402
from app.services.tpa_match_service import backfill_tpas_from_lousa_alocacao  # noqa: E402


async def seed(days: int = 14) -> dict[str, int]:
    async with session_scope() as db:
        return await backfill_tpas_from_lousa_alocacao(db, days=days)


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(seed())
    print("✅ seed_tpas_from_lousa:", result)
