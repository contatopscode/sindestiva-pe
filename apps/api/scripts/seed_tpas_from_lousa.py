"""SINDESTIVA-PE · Backfill de stubs TPA a partir de `lousa_alocacao`.

Requer `ALLOW_TPA_STUB=1`. Idempotente por `matricula_ogmo`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import session_scope  # noqa: E402
from app.services.tpa_stub_backfill_service import (  # noqa: E402
    backfill_stubs_from_lousa_alocacao,
)


async def seed(*, days: int = 30) -> dict:
    async with session_scope() as db:
        return await backfill_stubs_from_lousa_alocacao(db, days=days)


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(seed())
    print("✅ seed_tpas_from_lousa:", result)
