"""SINDESTIVA-PE · Migration 0003 — lousa_alocacao (Sprint 2).

Sprint 2 T2-02: tabela normalizada das células da lousa.

Cria:
  - 1 tabela: lousa_alocacao
  - 6 índices (1 UNIQUE composto, 5 secundários + 1 GIN no payload)

DD v1 §3.28. Forward-only (convenção do projeto).

Volume esperado: ~1.144 células/dia (26 funções × 11 fainas × 2 turnos ×
2 portos) × 365 = ~417k linhas/ano. Sem partição no MVP (Sprint 8).

LGPD: NÃO FK direta em `tpas.id` — apenas `trabalhador_matricula`
(chave funcional OGMO, nº público) + `trabalhador_id` NULLABLE para
reconciliação batch (Sprint 5 K-5).

Revision ID: 0003_lousa_alocacao
Revises: 0002_lousa_escala_origem
Create Date: 2026-09-01
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_lousa_alocacao"
down_revision: str | Sequence[str] | None = "0002_lousa_escala_origem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Schema default (DD v1 ADR-002 — schema único `lousa_main`).
SCHEMA = "lousa_main"


def upgrade() -> None:
    op.execute(f"SET search_path TO {SCHEMA}, public")

    # =========================================================================
    # TABELA: lousa_alocacao (DD v1 §3.28)
    # =========================================================================
    op.create_table(
        "lousa_alocacao",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        # FK para a origem do scrape (CASCADE — se origem for purgeada,
        # alocação vai junto).
        sa.Column("escala_origem_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Dimensões da lousa.
        sa.Column("porto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("faina_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("funcao_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Data da célula.
        sa.Column("data_referencia", sa.Date, nullable=False),
        # Identificação LGPD-safe do TPA.
        sa.Column("trabalhador_matricula", sa.Text, nullable=True),
        sa.Column("trabalhador_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Flags por categoria (1 se função escalada é da categoria, NULL caso contrário).
        sa.Column("fk_mando", sa.Integer, nullable=True),
        sa.Column("fk_terno", sa.Integer, nullable=True),
        sa.Column("fk_tecnica", sa.Integer, nullable=True),
        sa.Column("fk_vigia", sa.Integer, nullable=True),
        # Timestamps.
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        # FKs
        sa.ForeignKeyConstraint(
            ["escala_origem_id"], [f"{SCHEMA}.lousa_escala_origem.id"],
            ondelete="CASCADE", name="fk_alocacao_escala_origem",
        ),
        sa.ForeignKeyConstraint(
            ["porto_id"], [f"{SCHEMA}.portos.id"],
            ondelete="RESTRICT", name="fk_alocacao_porto",
        ),
        sa.ForeignKeyConstraint(
            ["turno_id"], [f"{SCHEMA}.turnos.id"],
            ondelete="RESTRICT", name="fk_alocacao_turno",
        ),
        sa.ForeignKeyConstraint(
            ["faina_id"], [f"{SCHEMA}.fainas.id"],
            ondelete="RESTRICT", name="fk_alocacao_faina",
        ),
        sa.ForeignKeyConstraint(
            ["funcao_id"], [f"{SCHEMA}.funcoes.id"],
            ondelete="RESTRICT", name="fk_alocacao_funcao",
        ),
        sa.ForeignKeyConstraint(
            ["trabalhador_id"], [f"{SCHEMA}.tpas.id"],
            ondelete="RESTRICT", name="fk_alocacao_trabalhador",
        ),
        # UNIQUE composto: 1 célula por (origem, faina, função).
        sa.UniqueConstraint(
            "escala_origem_id", "faina_id", "funcao_id",
            name="uq_alocacao_origem_faina_funcao",
        ),
        schema=SCHEMA,
    )

    # =========================================================================
    # ÍNDICES
    # =========================================================================
    op.create_index(
        "idx_alocacao_data_porto_turno", "lousa_alocacao",
        ["data_referencia", "porto_id", "turno_id"], schema=SCHEMA,
    )
    op.create_index(
        "idx_alocacao_faina", "lousa_alocacao",
        ["faina_id"], schema=SCHEMA,
    )
    op.create_index(
        "idx_alocacao_funcao", "lousa_alocacao",
        ["funcao_id"], schema=SCHEMA,
    )
    op.create_index(
        "idx_alocacao_trabalhador_matricula", "lousa_alocacao",
        ["trabalhador_matricula"], schema=SCHEMA,
    )
    op.create_index(
        "idx_alocacao_trabalhador_id", "lousa_alocacao",
        ["trabalhador_id"], schema=SCHEMA,
    )
    op.create_index(
        "idx_alocacao_escala_origem", "lousa_alocacao",
        ["escala_origem_id"], schema=SCHEMA,
    )


def downgrade() -> None:
    """Forward-only por convenção do projeto. Downgrade explícito
    deve ser uma migration reversa separada.
    """
    raise NotImplementedError(
        "Forward-only convention. Crie uma migration reversa explícita."
    )
