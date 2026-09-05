"""SINDESTIVA-PE · Base declarativa + mixins reutilizáveis.

Convenções (DD v1 §3, CONVENCOES.md):
  - PK = `id UUID` com default `gen_random_uuid()` (Postgres pgcrypto)
  - Timestamps: `created_at` + `updated_at` (server_default=now())
  - Soft delete: `deleted_at` nullable + `purge_after` (LGPD)
  - Datas em `DateTime(timezone=True)` — `timestamptz` no Postgres

A `DeclarativeBase` canônica fica em `app.core.database` (single source
of truth — assim o engine/session e o registry dos models ficam
co-localizados e evitamos warnings de classes Base duplicadas).
Aqui só reexportamos + adicionamos os mixins.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------

class TimestampMixin:
    """Adiciona `created_at` + `updated_at` (auto-preenchidos).

    A coluna `updated_at` é auto-atualizada no UPDATE via
    `onupdate=func.now()` (server-side, mas SQLAlchemy emite no
    statement).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """Adiciona `deleted_at` (nullable) + `purge_after` (LGPD 24m default).

    Uso:
        query.filter(Model.deleted_at.is_(None))  # ignora soft-deletados

    Para retenção diferente (ex: Fiscal = 5a, Dirigente = 24m), sobrescreva
    `purge_after` no model filho com `server_default` próprio. O DDL da
    migration 0001 reflete essas exceções (ver `fiscais.purge_after`).
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    purge_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        # server_default omitido — ver perfis_internos.py para rationale
        # (SQLAlchemy wrappa em string literal no DDL, Postgres não
        # consegue fazer cast para timestamptz). Adicionado via ALTER
        # TABLE no init endpoint.
    )


__all__ = ["Base", "TimestampMixin", "SoftDeleteMixin"]
