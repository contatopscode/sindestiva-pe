#!/usr/bin/env python3
# =============================================================================
# SINDESTIVA-PE · Seed inicial idempotente (Coolify/prod)
#
# Orquestra os seeds oficiais de users + TPAs demo (mesma ordem do
# `run-seeds.sh` e do `POST /api/v1/admin/run-seeds`, sem catálogos).
# Usado pelo entrypoint.sh da API no startup do container.
#
# Idempotência: delegada a seed_users e seed_tpas_demo (upsert por email/matricula).
# =============================================================================

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent

if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


async def seed_se_vazio() -> None:
    """Popula users e TPAs demo via seeds canônicos (idempotentes)."""
    from seed_users import seed as seed_users  # noqa: E402
    from seed_tpas_demo import seed as seed_tpas_demo  # noqa: E402

    print("    → Seed users (Paulo/Manoel/Josias)...")
    await seed_users(dry_run=False)
    print("    → Seed TPAs demo (TPA-001/TPA-002)...")
    await seed_tpas_demo()
    print("    ✓ Seed inicial OK")


if __name__ == "__main__":
    try:
        asyncio.run(seed_se_vazio())
    except Exception as e:
        print(f"ERRO: seed_initial falhou: {e}", file=sys.stderr)
        sys.exit(1)
