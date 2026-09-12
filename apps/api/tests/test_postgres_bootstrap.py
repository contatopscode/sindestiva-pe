"""Tests for postgres bootstrap helpers (no live DB)."""

from __future__ import annotations

from app.core.postgres_bootstrap import CRITICAL_TABLES, POSTGRES_EXTENSIONS


def test_extensions_match_migration_0001() -> None:
    assert POSTGRES_EXTENSIONS == ("pgcrypto", "citext", "pg_trgm")


def test_critical_tables_include_scraping() -> None:
    assert "lousa_escala_origem" in CRITICAL_TABLES
    assert "portos" in CRITICAL_TABLES
