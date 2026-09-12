#!/usr/bin/env python3
"""Alembic upgrade with drift repair (entrypoint step 1).

Detects alembic_version ahead of missing tables (e.g. portos,
lousa_escala_origem), stamps back safely, re-runs `upgrade head`, then
optional SQLAlchemy create_all fallback.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.postgres_bootstrap import run_migrations_with_drift_repair


def main() -> int:
    result = run_migrations_with_drift_repair()
    actions = ", ".join(result.get("actions", []))
    print(
        f"OK={result.get('ok')} repaired_drift={result.get('repaired_drift')} "
        f"revision {result.get('revision_before')} -> {result.get('revision_after')} "
        f"missing {result.get('missing_before')} -> {result.get('missing_after')} "
        f"actions=[{actions}]"
    )
    if not result.get("ok"):
        err = result.get("error") or "migrate/repair failed"
        print(f"ERRO: {err}", file=sys.stderr)
        tail = result.get("log_tail")
        if tail:
            print(tail[-2000:], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
