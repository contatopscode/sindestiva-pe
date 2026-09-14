"""SINDESTIVA-PE · Matcher matrícula OGMO ↔ cadastro TPA (Sprint 2 / T2-05).

Normalização mínima (trim) — **não** remove zeros à esquerda; a matrícula
exibida na lousa do OGMO deve bater exatamente com `tpas.matricula_ogmo`
após strip de espaços.
"""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tpa


def normalize_matricula_ogmo(matricula: str | None) -> str | None:
    """Strip de bordas; vazio → None."""
    if matricula is None:
        return None
    trimmed = matricula.strip()
    return trimmed if trimmed else None


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
    keys = {
        k
        for m in matriculas
        if (k := normalize_matricula_ogmo(m)) is not None
    }
    if not keys:
        return {}
    stmt = select(Tpa).where(Tpa.matricula_ogmo.in_(keys))
    rows = (await db.execute(stmt)).scalars().all()
    return {t.matricula_ogmo: t for t in rows}


__all__ = [
    "load_tpas_by_matriculas",
    "normalize_matricula_ogmo",
    "resolve_tpa_by_matricula",
]
