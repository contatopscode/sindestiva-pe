"""SINDESTIVA-PE · Migration 0005 — app_settings + OGMO WhatsApp destinatário.

- Tabela `lousa_main.app_settings` (key/value) para `ogmo_whatsapp`.
- Coluna `destinatario_whatsapp` em `ogmo_notificacoes`.
- Enum `canal_notificacao_enum` + CHECK destinatário alinhados ao canal WHATSAPP.

O valor de enum ``WHATSAPP`` é adicionado em conexão AUTOCOMMIT (commit próprio);
Postgres não permite usar um valor novo no mesmo transaction do ``ADD VALUE``.

Downgrade: não remove ``WHATSAPP`` de ``canal_notificacao_enum`` — Postgres não suporta
``DROP VALUE`` em tipos enum.

Revision ID: 0005_app_settings_ogmo_whatsapp
Revises: 0004_purge_after_server_default
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision: str = "0005_app_settings_ogmo_whatsapp"
down_revision: str | Sequence[str] | None = "0004_purge_after_server_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "lousa_main"

_ADD_WHATSAPP_ENUM = (
    "ALTER TYPE lousa_main.canal_notificacao_enum "
    "ADD VALUE IF NOT EXISTS 'WHATSAPP'"
)


def _add_canal_notificacao_whatsapp_enum_value() -> None:
    """ADD VALUE fora da transação Alembic (Coolify/HOM: sem autocommit_block)."""
    bind = op.get_bind()
    engine = bind.engine
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(_ADD_WHATSAPP_ENUM))


def upgrade() -> None:
    # Postgres: ADD VALUE must commit before WHATSAPP appears in CHECK (UnsafeNewEnumValueUsage).
    _add_canal_notificacao_whatsapp_enum_value()

    op.add_column(
        "ogmo_notificacoes",
        sa.Column("destinatario_whatsapp", sa.Text(), nullable=True),
        schema=SCHEMA,
    )

    op.drop_constraint(
        "ck_ogmo_notif_destinatario",
        "ogmo_notificacoes",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "ck_ogmo_notif_destinatario",
        "ogmo_notificacoes",
        "(canal = 'EMAIL' AND destinatario_email IS NOT NULL) "
        "OR (canal = 'WEBHOOK' AND destinatario_webhook_id IS NOT NULL) "
        "OR (canal = 'WHATSAPP' AND destinatario_whatsapp IS NOT NULL) "
        "OR (canal = 'PAINEL_OGMO')",
        schema=SCHEMA,
    )

    op.create_table(
        "app_settings",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{SCHEMA}.users.id"],
            ondelete="SET NULL",
            name="fk_app_settings_updated_by",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("app_settings", schema=SCHEMA)

    op.drop_constraint(
        "ck_ogmo_notif_destinatario",
        "ogmo_notificacoes",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "ck_ogmo_notif_destinatario",
        "ogmo_notificacoes",
        "(canal = 'EMAIL' AND destinatario_email IS NOT NULL) "
        "OR (canal = 'WEBHOOK' AND destinatario_webhook_id IS NOT NULL) "
        "OR (canal = 'PAINEL_OGMO')",
        schema=SCHEMA,
    )

    op.drop_column("ogmo_notificacoes", "destinatario_whatsapp", schema=SCHEMA)
