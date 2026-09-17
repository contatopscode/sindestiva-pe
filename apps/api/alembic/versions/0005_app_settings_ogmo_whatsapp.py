"""SINDESTIVA-PE · Migration 0005 — app_settings + OGMO WhatsApp destinatário.

- Tabela `lousa_main.app_settings` (key/value) para `ogmo_whatsapp`.
- Coluna `destinatario_whatsapp` em `ogmo_notificacoes`.
- Enum `canal_notificacao_enum` + CHECK destinatário alinhados ao canal WHATSAPP.

Revision ID: 0005_app_settings_ogmo_whatsapp
Revises: 0004_purge_after_server_default
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_app_settings_ogmo_whatsapp"
down_revision: str | Sequence[str] | None = "0004_purge_after_server_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "lousa_main"


def upgrade() -> None:
    op.execute(
        "ALTER TYPE lousa_main.canal_notificacao_enum "
        "ADD VALUE IF NOT EXISTS 'WHATSAPP'"
    )

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
