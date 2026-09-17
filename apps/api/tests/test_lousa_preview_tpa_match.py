"""SINDESTIVA-PE · Teste de preview lousa com matcher matrícula (sem DB)."""
from __future__ import annotations

from app.services.tpa_match_service import normalize_matricula_ogmo


def test_preview_matricula_lookup_key_uses_trim_only() -> None:
    raw = " 058 "
    assert normalize_matricula_ogmo(raw) == "058"
    # Simula chave usada no dict de batch lookup
    db_key = "058"
    assert normalize_matricula_ogmo(raw) == db_key
