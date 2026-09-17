"""Tests for postgres bootstrap helpers (no live DB)."""

from __future__ import annotations

from app.core.postgres_bootstrap import (
    CRITICAL_TABLES,
    DRIFT_ANCHOR_TABLES,
    POSTGRES_EXTENSIONS,
    REVISION_0001,
    REVISION_0002,
    compute_stamp_target_for_missing,
)


def test_extensions_match_migration_0001() -> None:
    assert POSTGRES_EXTENSIONS == ("pgcrypto", "citext", "pg_trgm")


def test_critical_tables_include_scraping() -> None:
    assert "lousa_escala_origem" in CRITICAL_TABLES
    assert "portos" in CRITICAL_TABLES
    assert "portos" in DRIFT_ANCHOR_TABLES


def test_stamp_target_portos_missing() -> None:
    assert compute_stamp_target_for_missing(["portos", "lousa_escala_origem"]) == "base"


def test_stamp_target_escala_origem_only() -> None:
    assert compute_stamp_target_for_missing(["lousa_escala_origem"]) == REVISION_0001


def test_stamp_target_alocacao_only() -> None:
    assert compute_stamp_target_for_missing(["lousa_alocacao"]) == REVISION_0002


def test_stamp_target_none_when_empty() -> None:
    assert compute_stamp_target_for_missing([]) is None


def test_scan_alembic_log_for_errors() -> None:
    from app.core.postgres_bootstrap import scan_alembic_log_for_errors

    log = "INFO ok\nERROR [alembic] something broke\n"
    hits = scan_alembic_log_for_errors(log)
    assert any("ERROR" in h for h in hits)
