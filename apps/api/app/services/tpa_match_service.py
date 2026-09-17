"""SINDESTIVA-PE · Matcher matrícula OGMO ↔ cadastro TPA (Sprint 2 / T2-05).

Normalização mínima (trim) — **não** remove zeros à esquerda; a matrícula
exibida na lousa do OGMO deve bater exatamente com `tpas.matricula_ogmo`
após strip de espaços.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tpa

# ck_tpas_matricula_ogmo (Alembic 0001): length BETWEEN 1 AND 10
MATRICULA_OGMO_MIN_LEN = 1
MATRICULA_OGMO_MAX_LEN = 10


def normalize_matricula_ogmo(matricula: str | None) -> str | None:
    """Strip de bordas; vazio → None."""
    if matricula is None:
        return None
    trimmed = matricula.strip()
    return trimmed if trimmed else None


def is_valid_matricula_ogmo_storage(matricula: str | None) -> bool:
    """True se a matrícula cabe em `tpas.matricula_ogmo` (CHECK length 1–10)."""
    key = normalize_matricula_ogmo(matricula)
    if not key:
        return False
    return MATRICULA_OGMO_MIN_LEN <= len(key) <= MATRICULA_OGMO_MAX_LEN


def split_matriculas_celula(raw: str | None) -> list[str]:
    """Expande célula OGMO (EscalaNet junta vários TPAs com vírgula) em tokens."""
    text = normalize_matricula_ogmo(raw)
    if not text:
        return []
    parts = re.split(r"[,;\s]+", text)
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        token = normalize_matricula_ogmo(part)
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def expand_matriculas_from_valores(valores: Iterable[str | None]) -> list[str]:
    """Flatten DISTINCT de valores de célula já splitados e válidos para stub."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in valores:
        for token in split_matriculas_celula(raw):
            if not is_valid_matricula_ogmo_storage(token):
                continue
            if token not in seen:
                seen.add(token)
                out.append(token)
    return out


async def resolve_tpa_by_matricula(
    db: AsyncSession,
    matricula: str | None,
) -> Tpa | None:
    """Resolve TPA por matrícula OGMO (exact match após trim)."""
    key = normalize_matricula_ogmo(matricula)
    if not key:
        return None
    stmt = select(Tpa).where(Tpa.matricula_ogmo == key)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def load_tpas_by_matriculas(
    db: AsyncSession,
    matriculas: Iterable[str | None],
) -> dict[str, Tpa]:
    """Batch lookup: chave = matrícula normalizada → Tpa."""
    keys = set(expand_matriculas_from_valores(matriculas))
    if not keys:
        return {}
    stmt = select(Tpa).where(Tpa.matricula_ogmo.in_(keys))
    rows = (await db.execute(stmt)).scalars().all()
    return {t.matricula_ogmo: t for t in rows}


__all__ = [
    "MATRICULA_OGMO_MAX_LEN",
    "MATRICULA_OGMO_MIN_LEN",
    "expand_matriculas_from_valores",
    "is_valid_matricula_ogmo_storage",
    "load_tpas_by_matriculas",
    "normalize_matricula_ogmo",
    "resolve_tpa_by_matricula",
    "split_matriculas_celula",
]
