"""SINDESTIVA-PE · Migration 0002 — lousa_escala_origem (Sprint 2).

Sprint 2 T2-01: persistir payload bruto de scraping com hash SHA-256.

Cria:
  - 2 enums novos: fonte_escala_enum, status_scraping_enum
  - 1 tabela: lousa_escala_origem
  - 6 índices (1 UNIQUE composto, 4 secundários, 1 GIN no payload_jsonb)

DD v1 §3.27. Forward-only (convenção do projeto).

Revision ID: 0002_lousa_escala_origem
Revises: 0001_initial_lousa_main
Create Date: 2026-09-01
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_lousa_escala_origem"
down_revision: str | Sequence[str] | None = "0001_initial_lousa_main"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Schema default (DD v1 ADR-002 — schema único `lousa_main`).
SCHEMA = "lousa_main"


def upgrade() -> None:
    # =========================================================================
    # 0. SEARCH PATH (obrigatório antes de qualquer DDL — ver migration 0001).
    # =========================================================================
    op.execute(f"SET search_path TO {SCHEMA}, public")

    # =========================================================================
    # 1. ENUMS novos
    # =========================================================================
    # `create_type=True` no construtor + uso na coluna = SQLAlchemy emite
    # `CREATE TYPE` automaticamente. Por isso NÃO chamamos .create() aqui
    # (a 0001 funciona pq chama .create() ANTES de usar o enum numa coluna,
    # mas nós já usamos na coluna abaixo, então o create_type=True basta).
    fonte_escala_enum = postgresql.ENUM(
        "TPA", "ESCALANET", "MANUAL_FISCAL",
        name="fonte_escala_enum", schema=SCHEMA, create_type=True,
    )
    status_scraping_enum = postgresql.ENUM(
        "SUCESSO", "PARCIAL", "FALHA", "LAYOUT_MUDOU", "SEM_DADOS",
        name="status_scraping_enum", schema=SCHEMA, create_type=True,
    )

    # =========================================================================
    # 2. TABELA: lousa_escala_origem (DD v1 §3.27)
    # =========================================================================
    op.create_table(
        "lousa_escala_origem",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        # Fonte do scrape (TPA Tecnologia, EscalaNet, ou manual).
        sa.Column("fonte", fonte_escala_enum, nullable=False),
        # Porto e turno (FKs criadas abaixo).
        sa.Column("porto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turno_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Data de referência da escala.
        sa.Column("data_referencia", sa.Date, nullable=False),
        # URL original (NULL quando MANUAL_FISCAL).
        sa.Column("url_origem", sa.Text, nullable=True),
        # SHA-256 hex do conteúdo (HTML bruto normalizado) — 64 chars.
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        # Payload bruto: HTML original + estrutura parseada + metadados.
        sa.Column("payload_jsonb", postgresql.JSONB, nullable=False),
        # Telemetria do scrape.
        sa.Column("duracao_ms", sa.Integer, nullable=False),
        sa.Column("status", status_scraping_enum, nullable=False,
                  server_default=sa.text("'SUCESSO'::status_scraping_enum")),
        sa.Column("erro_detalhes", sa.Text, nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        # FKs
        sa.ForeignKeyConstraint(
            ["porto_id"], [f"{SCHEMA}.portos.id"],
            ondelete="RESTRICT", name="fk_escala_origem_porto",
        ),
        sa.ForeignKeyConstraint(
            ["turno_id"], [f"{SCHEMA}.turnos.id"],
            ondelete="RESTRICT", name="fk_escala_origem_turno",
        ),
        # UNIQUE composto: idempotência do scrape.
        sa.UniqueConstraint(
            "fonte", "porto_id", "turno_id", "data_referencia",
            name="uq_escala_origem_fonte_porto_turno_data",
        ),
        schema=SCHEMA,
    )

    # =========================================================================
    # 3. ÍNDICES
    # =========================================================================
    op.create_index(
        "idx_escala_origem_data", "lousa_escala_origem",
        ["data_referencia"], schema=SCHEMA,
    )
    op.create_index(
        "idx_escala_origem_fonte", "lousa_escala_origem",
        ["fonte"], schema=SCHEMA,
    )
    op.create_index(
        "idx_escala_origem_status", "lousa_escala_origem",
        ["status"], schema=SCHEMA,
    )
    op.create_index(
        "idx_escala_origem_content_hash", "lousa_escala_origem",
        ["content_hash"], schema=SCHEMA,
    )
    op.create_index(
        "idx_escala_origem_payload_gin", "lousa_escala_origem",
        ["payload_jsonb"], postgresql_using="gin", schema=SCHEMA,
    )


def downgrade() -> None:
    """Forward-only por convenção do projeto. Downgrade explícito
    deve ser uma migration reversa separada.
    """
    raise NotImplementedError(
        "Forward-only convention. Crie uma migration reversa explícita."
    )
