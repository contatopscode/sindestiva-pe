#!/usr/bin/env python3
"""Bootstrap Postgres extensions before Alembic (entrypoint step 0).

Usage (container):
    python /app/scripts/ensure_db_extensions.py

Exits 0 on success, 1 on failure (Coolify should not mark service healthy).
"""
from __future__ import annotations

import sys
from pathlib import Path

# /app/scripts → /app (package `app`)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.postgres_bootstrap import ensure_schema_and_extensions


def main() -> int:
    try:
        result = ensure_schema_and_extensions()
    except Exception as exc:  # noqa: BLE001
        print(f"ERRO: bootstrap Postgres falhou: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    exts = ", ".join(result["extensions"])
    print(f"OK: schema={result['schema']} extensions=[{exts}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
