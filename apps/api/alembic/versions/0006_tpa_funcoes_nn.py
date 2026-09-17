"""SINDESTIVA-PE · Migration 0006 — tpa_funcoes N:N (FSW-2026-008).

Tabela de associação TPA ↔ funções + backfill a partir de funcao_base_id.

Revision ID: 0006_tpa_funcoes_nn
Revises: 0005_app_settings_ogmo_whatsapp
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_tpa_funcoes_nn"
down_revision: str | Sequence[str] | None = "0005_app_settings_ogmo_whatsapp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "lousa_main"


def upgrade() -> None:
    op.create_table(
        "tpa_funcoes",
        sa.Column("tpa_id", sa.Uuid(), nullable=False),
        sa.Column("funcao_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tpa_id"],
            [f"{SCHEMA}.tpas.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["funcao_id"],
            [f"{SCHEMA}.funcoes.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("tpa_id", "funcao_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_tpa_funcoes_funcao",
        "tpa_funcoes",
        ["funcao_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.tpa_funcoes (tpa_id, funcao_id, created_at)
            SELECT id, funcao_base_id, now()
            FROM {SCHEMA}.tpas
            WHERE deleted_at IS NULL
              AND funcao_base_id IS NOT NULL
            ON CONFLICT (tpa_id, funcao_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("idx_tpa_funcoes_funcao", table_name="tpa_funcoes", schema=SCHEMA)
    op.drop_table("tpa_funcoes", schema=SCHEMA)
