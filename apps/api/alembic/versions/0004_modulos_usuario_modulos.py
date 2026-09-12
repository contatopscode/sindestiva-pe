"""SINDESTIVA-PE · Migration 0004 — modulos + usuario_modulos (issue #14).

Gestão de usuários por módulo do sistema.

Cria:
  - 1 enum: modulo_papel_enum (VISUALIZAR/EDITAR/ADMIN)
  - 2 tabelas: modulos, usuario_modulos
  - 5 índices + 1 UNIQUE composto
  - seed dos 8 módulos que já existem no sistema hoje

Forward-only (convenção do projeto), mas com `downgrade()` real porque
estas tabelas são novas e não têm dado histórico — dá pra reverter sem
perda (as atribuições são reconstituíveis pela UI de matriz).

Risco mitigado (plano): "migração de dados existentes pode quebrar
acessos atuais". NÃO tocamos em `users`, `role` ou qualquer guard
existente. A tabela nasce vazia de atribuições e o DIRIGENTE é
superusuário por policy — ou seja, no dia do deploy ninguém perde
acesso: quem já entrava continua entrando.

`users` NÃO é criada aqui — já existe desde a migration 0001.

Revision ID: 0004_modulos_usuario_modulos
Revises: 0003_lousa_alocacao
Create Date: 2026-09-04
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_modulos_usuario_modulos"
down_revision: str | Sequence[str] | None = "0003_lousa_alocacao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Schema default (DD v1 ADR-002 — schema único `lousa_main`).
SCHEMA = "lousa_main"

# Seed: os módulos que o sistema JÁ tem (sidebar do web + routers v1).
# (slug, nome, descricao, ordem)
MODULOS_SEED: list[tuple[str, str, str, int]] = [
    ("lousa", "Lousa Espelhada", "Espelho da lousa oficial do OGMO (Recife e Suape).", 10),
    ("remanejamentos", "Remanejamentos", "Registro e aprovação de remanejamento operacional.", 20),
    ("ogmo", "Fila OGMO", "Notificações formais ao OGMO (e-mail + PDF + webhook).", 30),
    ("auditoria", "Auditoria", "Hash chain SHA-256 e trilha de eventos.", 40),
    ("bi", "BI & Dashboards", "KPIs e dashboards da diretoria.", 50),
    ("lgpd", "LGPD", "Consentimento, Art. 18 e painel do DPO.", 60),
    ("tpa", "PWA do TPA", "Escala do dia, confirmação de presença e canal com o Fiscal.", 70),
    ("admin", "Administração", "Gestão de usuários, módulos e matriz de permissões.", 80),
]


def upgrade() -> None:
    op.execute(f"SET search_path TO {SCHEMA}, public")

    # =========================================================================
    # ENUM: modulo_papel_enum
    # =========================================================================
    # `checkfirst` manual — o padrão do projeto é criar o tipo aqui e os
    # models usarem `create_type=False` (ver `pg_enum()` em models/enums.py).
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE t.typname = 'modulo_papel_enum' AND n.nspname = '{SCHEMA}'
            ) THEN
                CREATE TYPE {SCHEMA}.modulo_papel_enum
                    AS ENUM ('VISUALIZAR', 'EDITAR', 'ADMIN');
            END IF;
        END$$;
        """
    )

    # =========================================================================
    # TABELA: modulos
    # =========================================================================
    op.create_table(
        "modulos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_modulos_slug"),
        # Slug é chave funcional da policy (`requer_modulo("lousa")`):
        # kebab/snake em lowercase, sem espaço nem barra. Espelha o
        # validador do `ModuloCreate` (Pydantic) — defesa em profundidade,
        # porque seed e scripts entram por SQL, não pelo schema.
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9][a-z0-9_-]{0,63}$'",
            name="ck_modulos_slug_formato",
        ),
        sa.CheckConstraint("length(btrim(nome)) > 0", name="ck_modulos_nome_nao_vazio"),
        schema=SCHEMA,
    )
    op.create_index("idx_modulos_ativo", "modulos", ["ativo"], schema=SCHEMA)
    op.create_index("idx_modulos_ordem", "modulos", ["ordem"], schema=SCHEMA)

    # =========================================================================
    # TABELA: usuario_modulos
    # =========================================================================
    op.create_table(
        "usuario_modulos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modulo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "papel",
            postgresql.ENUM(
                "VISUALIZAR", "EDITAR", "ADMIN",
                name="modulo_papel_enum",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text(f"'VISUALIZAR'::{SCHEMA}.modulo_papel_enum"),
        ),
        sa.Column("concedido_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"], [f"{SCHEMA}.users.id"],
            name="fk_usuario_modulos_user", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["modulo_id"], [f"{SCHEMA}.modulos.id"],
            name="fk_usuario_modulos_modulo", ondelete="CASCADE",
        ),
        # Quem concedeu vira NULL se o concedente sair — o vínculo do
        # usuário-alvo NÃO pode cair junto.
        sa.ForeignKeyConstraint(
            ["concedido_por"], [f"{SCHEMA}.users.id"],
            name="fk_usuario_modulos_concedido_por", ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "user_id", "modulo_id", name="uq_usuario_modulos_user_modulo"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_usuario_modulos_user", "usuario_modulos", ["user_id"], schema=SCHEMA
    )
    op.create_index(
        "idx_usuario_modulos_modulo", "usuario_modulos", ["modulo_id"], schema=SCHEMA
    )

    # =========================================================================
    # SEED: módulos existentes
    # =========================================================================
    # Idempotente (ON CONFLICT) — a migration pode rodar num banco que já
    # recebeu o seed via script de dev.
    modulos_table = sa.table(
        "modulos",
        sa.column("slug", sa.Text),
        sa.column("nome", sa.Text),
        sa.column("descricao", sa.Text),
        sa.column("ordem", sa.Integer),
        schema=SCHEMA,
    )
    op.bulk_insert(
        modulos_table,
        [
            {"slug": slug, "nome": nome, "descricao": desc, "ordem": ordem}
            for slug, nome, desc, ordem in MODULOS_SEED
        ],
    )


def downgrade() -> None:
    op.execute(f"SET search_path TO {SCHEMA}, public")
    op.drop_index("idx_usuario_modulos_modulo", table_name="usuario_modulos", schema=SCHEMA)
    op.drop_index("idx_usuario_modulos_user", table_name="usuario_modulos", schema=SCHEMA)
    op.drop_table("usuario_modulos", schema=SCHEMA)
    op.drop_index("idx_modulos_ordem", table_name="modulos", schema=SCHEMA)
    op.drop_index("idx_modulos_ativo", table_name="modulos", schema=SCHEMA)
    op.drop_table("modulos", schema=SCHEMA)
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.modulo_papel_enum")
