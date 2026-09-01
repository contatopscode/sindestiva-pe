"""SINDESTIVA-PE · Migration 0001 — schema inicial lousa_main.

Cria TODAS as 25 tabelas do DD v1 §3 (DD declara 26 no resumo
executivo mas §3 lista 25 — o `roles` é ENUM, não tabela, conforme
DD §3.2 — ver nota no final deste arquivo). Inclui:

  - 13 enums de domínio
  - Extensões: pgcrypto (já vem do init.sql), citext, pg_trgm
  - 25 tabelas
  - Todos os índices do DD v1 §3
  - CHECK constraints (formato CPF, matrícula, senha, etc)
  - FK com ON DELETE policy correta
  - 4 triggers append-only (termos, audit, access, purge)
  - 1 sequence para audit_events.sequencia

Forward-only por convenção do projeto (Paulo) — `downgrade()` é
placeholder vazio (rollback manual via migration reversa explícita).

Revision ID: 0001_initial_lousa_main
Revises:
Create Date: 2026-09-01
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_lousa_main"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Schema default (DD v1 ADR-002 — schema único `lousa_main`)
SCHEMA = "lousa_main"


def upgrade() -> None:
    # =========================================================================
    # 0. SEARCH PATH (obrigatório antes de qualquer DDL)
    # =========================================================================
    # Sem o `SET search_path` na transação, o Postgres procura os tipos
    # ENUM (role_enum, user_status_enum, etc) em `public` em vez de
    # `lousa_main`, mesmo com `schema="lousa_main"` no ENUM(). O init.sql
    # do container define search_path por DATABASE, mas ao conectar via
    # Alembic/psycopg, o search_path volta ao default do role.
    op.execute(f"SET search_path TO {SCHEMA}, public")

    # =========================================================================
    # 1. EXTENSÕES
    # =========================================================================
    # pgcrypto já vem do init.sql; garantimos idempotência.
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "citext"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # =========================================================================
    # 2. ENUMS (DD v1 §3 — 13 enums de domínio)
    # =========================================================================
    role_enum = postgresql.ENUM(
        "FISCAL", "DIRIGENTE", "TPA",
        name="role_enum", schema=SCHEMA, create_type=True,
    )
    user_status_enum = postgresql.ENUM(
        "PENDENTE_ACEITE", "ATIVO", "BLOQUEADO", "INATIVO",
        name="user_status_enum", schema=SCHEMA, create_type=True,
    )
    tpa_status_enum = postgresql.ENUM(
        "ATIVO", "AFASTADO", "DESLIGADO", "SUSPENSO",
        name="tpa_status_enum", schema=SCHEMA, create_type=True,
    )
    fiscal_status_enum = postgresql.ENUM(
        "ATIVO", "AFASTADO", "DESLIGADO",
        name="fiscal_status_enum", schema=SCHEMA, create_type=True,
    )
    snapshot_status_enum = postgresql.ENUM(
        "OK", "PARCIAL", "ERRO", "LAYOUT_MUDOU",
        name="snapshot_status_enum", schema=SCHEMA, create_type=True,
    )
    cell_status_enum = postgresql.ENUM(
        "NORMAL", "AUSENTE", "REMANEJADO", "CONFIRMADO",
        name="cell_status_enum", schema=SCHEMA, create_type=True,
    )
    motivo_remanejamento_enum = postgresql.ENUM(
        "ATESTADO_MEDICO", "FALTA_INJUSTIFICADA", "REFORCO_TERNO",
        "TROCA_TURNO", "ATRASO_15MIN", "FALTA_EPI",
        "LIBERACAO_ANTECIPADA", "OUTRO",
        name="motivo_remanejamento_enum", schema=SCHEMA, create_type=True,
    )
    status_remanejamento_enum = postgresql.ENUM(
        "PENDENTE", "APROVADO", "NOTIFICADO_OGMO",
        "ACK", "NACK", "CANCELADO",
        name="status_remanejamento_enum", schema=SCHEMA, create_type=True,
    )
    canal_notificacao_enum = postgresql.ENUM(
        "EMAIL", "WEBHOOK", "PAINEL_OGMO",
        name="canal_notificacao_enum", schema=SCHEMA, create_type=True,
    )
    status_notificacao_enum = postgresql.ENUM(
        "PENDENTE", "ENVIADO", "ENTREGUE", "FALHOU", "REJEITADO",
        name="status_notificacao_enum", schema=SCHEMA, create_type=True,
    )
    termo_metodo_enum = postgresql.ENUM(
        "PRIMEIRO_LOGIN", "RECONFIRMACAO", "ALTERACAO_TERMO", "REVOGACAO",
        name="termo_metodo_enum", schema=SCHEMA, create_type=True,
    )
    lgpd_tipo_enum = postgresql.ENUM(
        "EXCLUSAO", "PORTABILIDADE", "CORRECAO",
        "CONFIRMACAO_EXISTENCIA", "REVOGACAO_CONSENTIMENTO",
        name="lgpd_tipo_enum", schema=SCHEMA, create_type=True,
    )
    lgpd_status_enum = postgresql.ENUM(
        "RECEBIDA", "EM_ANALISE", "DEFERIDA", "INDEFERIDA", "EXECUTADA",
        name="lgpd_status_enum", schema=SCHEMA, create_type=True,
    )

    role_enum.create(op.get_bind(), checkfirst=True)
    user_status_enum.create(op.get_bind(), checkfirst=True)
    tpa_status_enum.create(op.get_bind(), checkfirst=True)
    fiscal_status_enum.create(op.get_bind(), checkfirst=True)
    snapshot_status_enum.create(op.get_bind(), checkfirst=True)
    cell_status_enum.create(op.get_bind(), checkfirst=True)
    motivo_remanejamento_enum.create(op.get_bind(), checkfirst=True)
    status_remanejamento_enum.create(op.get_bind(), checkfirst=True)
    canal_notificacao_enum.create(op.get_bind(), checkfirst=True)
    status_notificacao_enum.create(op.get_bind(), checkfirst=True)
    termo_metodo_enum.create(op.get_bind(), checkfirst=True)
    lgpd_tipo_enum.create(op.get_bind(), checkfirst=True)
    lgpd_status_enum.create(op.get_bind(), checkfirst=True)

    # =========================================================================
    # 3. TABELAS DE CATÁLOGO (sem FK; criadas primeiro)
    # =========================================================================

    # ---- portos (DD v1 §3.6)
    op.create_table(
        "portos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("codigo", sa.Text, nullable=False),
        sa.Column("nome_completo", sa.Text, nullable=False),
        sa.Column("cnpj_ogmo", sa.Text, nullable=True),
        sa.Column("url_tpa", sa.Text, nullable=True),
        sa.Column("url_escalanet", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("codigo", name="uq_portos_codigo"),
        schema=SCHEMA,
    )

    # ---- turnos (DD v1 §3.7)
    op.create_table(
        "turnos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("codigo", sa.Text, nullable=False),
        sa.Column("nome_exibicao", sa.Text, nullable=False),
        sa.Column("hora_inicio", sa.Time, nullable=False),
        sa.Column("hora_fim", sa.Time, nullable=False),
        sa.Column("duracao_horas", sa.Numeric(4, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("codigo", name="uq_turnos_codigo"),
        schema=SCHEMA,
    )

    # ---- funcoes (DD v1 §3.8) — categoria como TEXT (não enum) por
    # simplicidade, mas com CHECK para garantir valores válidos.
    op.create_table(
        "funcoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("codigo", sa.Text, nullable=False),
        sa.Column("nome_exibicao", sa.Text, nullable=False),
        sa.Column("categoria", sa.Text, nullable=False),
        sa.Column("ordem_lousa", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("codigo", name="uq_funcoes_codigo"),
        sa.UniqueConstraint("ordem_lousa", name="uq_funcoes_ordem"),
        sa.CheckConstraint(
            "categoria IN ('MANDO','TERNO','TECNICA','VIGIA')",
            name="ck_funcoes_categoria",
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_funcoes_categoria", "funcoes", ["categoria"], schema=SCHEMA)
    op.create_index(
        "idx_funcoes_nome_trgm", "funcoes", ["nome_exibicao"],
        postgresql_using="gin",
        postgresql_ops={"nome_exibicao": "gin_trgm_ops"},
        schema=SCHEMA,
    )

    # ---- fainas (DD v1 §3.9)
    op.create_table(
        "fainas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("codigo", sa.Text, nullable=False),
        sa.Column("nome_exibicao", sa.Text, nullable=False),
        sa.Column("cor_hex", sa.Text, nullable=True),
        sa.Column("ordem_lousa", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("codigo", name="uq_fainas_codigo"),
        sa.UniqueConstraint("ordem_lousa", name="uq_fainas_ordem"),
        schema=SCHEMA,
    )

    # ---- navios (DD v1 §3.10)
    op.create_table(
        "navios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("nome", sa.Text, nullable=False),
        sa.Column("imo", sa.Text, nullable=True),
        sa.Column("bandeira", sa.Text, nullable=True),
        sa.Column("tipo_operacao", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("imo", name="uq_navios_imo"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_navios_nome_trgm", "navios", ["nome"],
        postgresql_using="gin",
        postgresql_ops={"nome": "gin_trgm_ops"},
        schema=SCHEMA,
    )

    # ---- cct_clausulas (DD v1 §3.11)
    op.create_table(
        "cct_clausulas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("versao_cct", sa.Text, nullable=False),
        sa.Column("clausula", sa.Text, nullable=False),
        sa.Column("descricao", sa.Text, nullable=False),
        sa.Column("motivos_vinculados", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("versao_cct", "clausula", name="uq_cct_versao_clausula"),
        schema=SCHEMA,
    )
    op.create_index("idx_cct_versao", "cct_clausulas", ["versao_cct"], schema=SCHEMA)
    op.create_index(
        "idx_cct_motivos_gin", "cct_clausulas", ["motivos_vinculados"],
        postgresql_using="gin", schema=SCHEMA,
    )

    # ---- feriados_nacionais (DD v1 §3.26)
    op.create_table(
        "feriados_nacionais",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("data", sa.Date, nullable=False),
        sa.Column("nome", sa.Text, nullable=False),
        sa.Column("tipo", sa.Text, nullable=False),
        sa.Column("is_recorrente", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("data", name="uq_feriados_data"),
        sa.CheckConstraint(
            "tipo IN ('NACIONAL','ESTADUAL_PE','MUNICIPAL_SUAPE','MUNICIPAL_RECIFE')",
            name="ck_feriados_tipo",
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_feriados_tipo", "feriados_nacionais", ["tipo"], schema=SCHEMA)

    # =========================================================================
    # 4. AUTH (DD v1 §3.1)
    # =========================================================================

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("telefone", sa.Text, nullable=True),
        sa.Column("password_hash", sa.Text, nullable=True),
        sa.Column("role", postgresql.ENUM(name="role_enum", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM(name="user_status_enum", create_type=False),
                  nullable=False, server_default=sa.text("'PENDENTE_ACEITE'::user_status_enum")),
        sa.Column("failed_login_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", postgresql.INET, nullable=True),
        sa.Column("last_login_user_agent", sa.Text, nullable=True),
        sa.Column("accepted_terms_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_terms_version", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + INTERVAL '24 months'")),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(
            "(email IS NOT NULL) OR (telefone IS NOT NULL)",
            name="ck_users_email_or_telefone",
        ),
        # TODO(D1): TPA password — check atual é conservador (TPA sem
        # senha). Se Paulo confirmar (b) TPA pode ter senha, remover
        # esta constraint.
        sa.CheckConstraint(
            "(role <> 'TPA') OR (password_hash IS NULL)",
            name="ck_users_password_for_non_tpa",
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_users_role", "users", ["role"], schema=SCHEMA)
    op.create_index("idx_users_status", "users", ["status"], schema=SCHEMA)
    op.create_index("idx_users_created_at", "users", ["created_at"], schema=SCHEMA)
    op.create_index(
        "idx_users_deleted_at", "users", ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"), schema=SCHEMA,
    )
    op.create_index("idx_users_purge_after", "users", ["purge_after"], schema=SCHEMA)
    op.create_index("idx_users_telefone", "users", ["telefone"], schema=SCHEMA)

    # =========================================================================
    # 5. PERFIS DE NEGÓCIO 1:1 COM USERS (DD v1 §3.3, §3.4, §3.5)
    # =========================================================================

    # ---- tpas (DD v1 §3.3)
    op.create_table(
        "tpas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cpf", postgresql.CITEXT(), nullable=False),
        sa.Column("nome_completo", sa.Text, nullable=False),
        sa.Column("matricula_ogmo", sa.Text, nullable=False),
        sa.Column("data_nascimento", sa.Date, nullable=True),
        sa.Column("telefone", sa.Text, nullable=False),
        sa.Column("funcao_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria", sa.Text, nullable=False),
        sa.Column("status_cadastro", postgresql.ENUM(name="tpa_status_enum", create_type=False),
                  nullable=False, server_default=sa.text("'ATIVO'::tpa_status_enum")),
        sa.Column("data_admissao", sa.Date, nullable=True),
        sa.Column("data_desligamento", sa.Date, nullable=True),
        sa.Column("consentimento_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consentimento_versao", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + INTERVAL '24 months'")),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT",
                                 name="fk_tpas_user"),
        sa.ForeignKeyConstraint(["funcao_base_id"], [f"{SCHEMA}.funcoes.id"], ondelete="RESTRICT",
                                 name="fk_tpas_funcao_base"),
        sa.UniqueConstraint("user_id", name="uq_tpas_user_id"),
        sa.UniqueConstraint("cpf", name="uq_tpas_cpf"),
        sa.UniqueConstraint("matricula_ogmo", name="uq_tpas_matricula_ogmo"),
        sa.CheckConstraint("cpf ~ '^\\d{11}$'", name="ck_tpas_cpf"),
        sa.CheckConstraint("length(matricula_ogmo) BETWEEN 1 AND 10", name="ck_tpas_matricula_ogmo"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_tpas_nome_trgm", "tpas", ["nome_completo"],
        postgresql_using="gin",
        postgresql_ops={"nome_completo": "gin_trgm_ops"},
        schema=SCHEMA,
    )
    op.create_index("idx_tpas_funcao_base", "tpas", ["funcao_base_id"], schema=SCHEMA)
    op.create_index("idx_tpas_categoria", "tpas", ["categoria"], schema=SCHEMA)
    op.create_index("idx_tpas_status_cadastro", "tpas", ["status_cadastro"], schema=SCHEMA)
    op.create_index("idx_tpas_data_desligamento", "tpas", ["data_desligamento"], schema=SCHEMA)
    op.create_index("idx_tpas_telefone", "tpas", ["telefone"], schema=SCHEMA)
    op.create_index("idx_tpas_purge_after", "tpas", ["purge_after"], schema=SCHEMA)
    op.create_index(
        "idx_tpas_deleted_at", "tpas", ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"), schema=SCHEMA,
    )

    # ---- fiscais (DD v1 §3.4)
    # Retenção 5a (D2) — purge_after default próprio.
    op.create_table(
        "fiscais",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cpf", postgresql.CITEXT(), nullable=False),
        sa.Column("nome_completo", sa.Text, nullable=False),
        sa.Column("matricula_sindicato", sa.Text, nullable=False),
        sa.Column("telefone", sa.Text, nullable=False),
        sa.Column("porto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", postgresql.ENUM(name="fiscal_status_enum", create_type=False),
                  nullable=False, server_default=sa.text("'ATIVO'::fiscal_status_enum")),
        sa.Column("data_inicio", sa.Date, nullable=False),
        sa.Column("data_fim", sa.Date, nullable=True),
        sa.Column("aprovador_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + INTERVAL '5 years'")),  # D2
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT",
                                 name="fk_fiscais_user"),
        sa.ForeignKeyConstraint(["porto_id"], [f"{SCHEMA}.portos.id"], ondelete="RESTRICT",
                                 name="fk_fiscais_porto"),
        sa.ForeignKeyConstraint(["turno_id"], [f"{SCHEMA}.turnos.id"], ondelete="RESTRICT",
                                 name="fk_fiscais_turno"),
        sa.ForeignKeyConstraint(["aprovador_id"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT",
                                 name="fk_fiscais_aprovador"),
        sa.UniqueConstraint("user_id", name="uq_fiscais_user_id"),
        sa.UniqueConstraint("cpf", name="uq_fiscais_cpf"),
        sa.UniqueConstraint("matricula_sindicato", name="uq_fiscais_matricula_sindicato"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_fiscais_nome_trgm", "fiscais", ["nome_completo"],
        postgresql_using="gin",
        postgresql_ops={"nome_completo": "gin_trgm_ops"},
        schema=SCHEMA,
    )
    op.create_index("idx_fiscais_porto", "fiscais", ["porto_id"], schema=SCHEMA)
    op.create_index("idx_fiscais_status", "fiscais", ["status"], schema=SCHEMA)
    op.create_index(
        "idx_fiscais_deleted_at", "fiscais", ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"), schema=SCHEMA,
    )

    # ---- dirigentes (DD v1 §3.5)
    op.create_table(
        "dirigentes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cpf", postgresql.CITEXT(), nullable=False),
        sa.Column("nome_completo", sa.Text, nullable=False),
        sa.Column("cargo", sa.Text, nullable=False),
        sa.Column("matricula_sindicato", sa.Text, nullable=False),
        sa.Column("is_dpo", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("data_inicio_mandato", sa.Date, nullable=False),
        sa.Column("data_fim_mandato", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + INTERVAL '5 years'")),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT",
                                 name="fk_dirigentes_user"),
        sa.UniqueConstraint("user_id", name="uq_dirigentes_user_id"),
        sa.UniqueConstraint("cpf", name="uq_dirigentes_cpf"),
        sa.UniqueConstraint("matricula_sindicato", name="uq_dirigentes_matricula"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_dirigentes_deleted_at", "dirigentes", ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"), schema=SCHEMA,
    )
    # Trigger que garante apenas 1 is_dpo = true ativo (DD v1 §3.5)
    op.execute("""
        CREATE OR REPLACE FUNCTION lousa_main.fn_dirigentes_dpo_unico()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.is_dpo = true THEN
                IF EXISTS (
                    SELECT 1 FROM lousa_main.dirigentes
                    WHERE is_dpo = true
                      AND deleted_at IS NULL
                      AND id <> NEW.id
                ) THEN
                    RAISE EXCEPTION 'DIRIGENTES_DPO_DUPLICADO: apenas 1 dirigente pode ter is_dpo = true'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER tg_dirigentes_dpo_unico
        BEFORE INSERT OR UPDATE OF is_dpo ON lousa_main.dirigentes
        FOR EACH ROW
        EXECUTE FUNCTION lousa_main.fn_dirigentes_dpo_unico();
    """)

    # =========================================================================
    # 6. LOUSA (DD v1 §3.12, §3.13, §3.25)
    # =========================================================================

    # ---- layout_fingerprints (DD v1 §3.25) — antes de lousa_snapshots (FK)
    op.create_table(
        "layout_fingerprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("porto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("versao", sa.Integer, nullable=False),
        sa.Column("html_hash_sha256", sa.CHAR(64), nullable=False),
        sa.Column("seletores_parser", postgresql.JSONB, nullable=False),
        sa.Column("fingerprint_estrutura", postgresql.JSONB, nullable=False),
        sa.Column("total_snapshots_validados", sa.BigInteger, nullable=False, server_default=sa.text("0")),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("detectado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("substituido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["porto_id"], [f"{SCHEMA}.portos.id"], ondelete="RESTRICT",
                                 name="fk_layout_fingerprints_porto"),
        sa.UniqueConstraint("porto_id", "versao", name="uq_fingerprints_porto_versao"),
        schema=SCHEMA,
    )
    # UNIQUE parcial: apenas 1 is_current = true por porto
    op.execute("""
        CREATE UNIQUE INDEX uq_fingerprints_porto_current
        ON lousa_main.layout_fingerprints (porto_id)
        WHERE is_current = true;
    """)
    op.create_index(
        "idx_fingerprints_seletores_gin", "layout_fingerprints", ["seletores_parser"],
        postgresql_using="gin", schema=SCHEMA,
    )
    op.create_index(
        "idx_fingerprints_estrutura_gin", "layout_fingerprints", ["fingerprint_estrutura"],
        postgresql_using="gin", schema=SCHEMA,
    )

    # ---- lousa_snapshots (DD v1 §3.12) — sem soft delete (DD v1 §3.12)
    op.create_table(
        "lousa_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("porto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fonte", sa.Text, nullable=False),
        sa.Column("url_origem", sa.Text, nullable=True),
        sa.Column("html_hash_sha256", sa.CHAR(64), nullable=False),
        sa.Column("layout_fingerprint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_celulas", sa.Integer, nullable=False),
        sa.Column("total_tpas_escalados", sa.Integer, nullable=False),
        sa.Column("duracao_scrape_ms", sa.Integer, nullable=False),
        sa.Column("status", postgresql.ENUM(name="snapshot_status_enum", create_type=False),
                  nullable=False, server_default=sa.text("'OK'::snapshot_status_enum")),
        sa.Column("erro_detalhes", sa.Text, nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["porto_id"], [f"{SCHEMA}.portos.id"], ondelete="RESTRICT",
                                 name="fk_lousa_snapshots_porto"),
        sa.ForeignKeyConstraint(["turno_id"], [f"{SCHEMA}.turnos.id"], ondelete="RESTRICT",
                                 name="fk_lousa_snapshots_turno"),
        sa.ForeignKeyConstraint(["layout_fingerprint_id"],
                                 [f"{SCHEMA}.layout_fingerprints.id"], ondelete="SET NULL",
                                 name="fk_lousa_snapshots_fingerprint"),
        schema=SCHEMA,
    )
    op.create_index("idx_lousa_snapshots_porto_turno_scraped", "lousa_snapshots",
                    ["porto_id", "turno_id", "scraped_at"], schema=SCHEMA)
    op.create_index("idx_lousa_snapshots_porto_created", "lousa_snapshots",
                    ["porto_id", "created_at"], schema=SCHEMA)
    op.create_index("idx_lousa_snapshots_scraped_at", "lousa_snapshots", ["scraped_at"], schema=SCHEMA)
    op.create_index("idx_lousa_snapshots_html_hash", "lousa_snapshots",
                    ["html_hash_sha256"], schema=SCHEMA)
    op.create_index("idx_lousa_snapshots_layout_fingerprint", "lousa_snapshots",
                    ["layout_fingerprint_id"], schema=SCHEMA)
    op.create_index("idx_lousa_snapshots_status", "lousa_snapshots", ["status"], schema=SCHEMA)

    # ---- lousa_cells (DD v1 §3.13) — sem soft delete (DD v1 §3.12 obs)
    op.create_table(
        "lousa_cells",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("porto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("funcao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("faina_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cais", sa.Text, nullable=True),
        sa.Column("navio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tpa_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status_celula", postgresql.ENUM(name="cell_status_enum", create_type=False),
                  nullable=False, server_default=sa.text("'NORMAL'::cell_status_enum")),
        sa.Column("data_referencia", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["snapshot_id"], [f"{SCHEMA}.lousa_snapshots.id"], ondelete="CASCADE",
                                 name="fk_lousa_cells_snapshot"),
        sa.ForeignKeyConstraint(["porto_id"], [f"{SCHEMA}.portos.id"], ondelete="RESTRICT",
                                 name="fk_lousa_cells_porto"),
        sa.ForeignKeyConstraint(["turno_id"], [f"{SCHEMA}.turnos.id"], ondelete="RESTRICT",
                                 name="fk_lousa_cells_turno"),
        sa.ForeignKeyConstraint(["funcao_id"], [f"{SCHEMA}.funcoes.id"], ondelete="RESTRICT",
                                 name="fk_lousa_cells_funcao"),
        sa.ForeignKeyConstraint(["faina_id"], [f"{SCHEMA}.fainas.id"], ondelete="RESTRICT",
                                 name="fk_lousa_cells_faina"),
        sa.ForeignKeyConstraint(["navio_id"], [f"{SCHEMA}.navios.id"], ondelete="SET NULL",
                                 name="fk_lousa_cells_navio"),
        sa.ForeignKeyConstraint(["tpa_id"], [f"{SCHEMA}.tpas.id"], ondelete="RESTRICT",
                                 name="fk_lousa_cells_tpa"),
        sa.UniqueConstraint("snapshot_id", "funcao_id", "faina_id", name="uq_lousa_cells_unique"),
        schema=SCHEMA,
    )
    op.create_index("idx_lousa_cells_porto_turno_data_funcao_faina", "lousa_cells",
                    ["porto_id", "turno_id", "data_referencia", "funcao_id", "faina_id"], schema=SCHEMA)
    op.create_index("idx_lousa_cells_tpa_data", "lousa_cells",
                    ["tpa_id", "data_referencia"], schema=SCHEMA)
    op.create_index("idx_lousa_cells_cais_data", "lousa_cells",
                    ["cais", "data_referencia"], schema=SCHEMA)
    op.create_index("idx_lousa_cells_navio", "lousa_cells", ["navio_id"], schema=SCHEMA)
    op.create_index("idx_lousa_cells_status", "lousa_cells", ["status_celula"], schema=SCHEMA)
    op.create_index("idx_lousa_cells_data", "lousa_cells", ["data_referencia"], schema=SCHEMA)
    op.create_index("idx_lousa_cells_snapshot", "lousa_cells", ["snapshot_id"], schema=SCHEMA)

    # =========================================================================
    # 7. REMANEJAMENTO (DD v1 §3.14, §3.15)
    # =========================================================================

    # ---- remanejamentos (DD v1 §3.14)
    # Retenção 5a — purge_after default próprio.
    op.create_table(
        "remanejamentos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("codigo_se", sa.Text, nullable=False),
        sa.Column("snapshot_origem_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("porto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_referencia", sa.Date, nullable=False),
        sa.Column("tpa_out_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("funcao_origem_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("faina_origem_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cais_origem", sa.Text, nullable=True),
        sa.Column("tpa_in_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("motivo", postgresql.ENUM(name="motivo_remanejamento_enum", create_type=False), nullable=False),
        sa.Column("motivo_outro_texto", sa.Text, nullable=True),
        sa.Column("base_legal_cct_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_legal_texto_livre", sa.Text, nullable=True),
        sa.Column("observacoes", sa.Text, nullable=True),
        sa.Column("anexo_url", sa.Text, nullable=True),
        sa.Column("fiscal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", postgresql.ENUM(name="status_remanejamento_enum", create_type=False),
                  nullable=False, server_default=sa.text("'PENDENTE'::status_remanejamento_enum")),
        sa.Column("ack_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ack_por", sa.Text, nullable=True),
        sa.Column("nack_motivo", sa.Text, nullable=True),
        # TODO(D8): hash_evento em remanejamentos. Recomendação = remover
        # (cadeia única em audit_events). Mantido conforme DD v1.
        sa.Column("hash_evento", sa.CHAR(64), nullable=False),
        sa.Column("hash_anterior_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + INTERVAL '5 years'")),
        sa.ForeignKeyConstraint(["snapshot_origem_id"], [f"{SCHEMA}.lousa_snapshots.id"],
                                 ondelete="RESTRICT", name="fk_remanejamentos_snapshot"),
        sa.ForeignKeyConstraint(["porto_id"], [f"{SCHEMA}.portos.id"], ondelete="RESTRICT",
                                 name="fk_remanejamentos_porto"),
        sa.ForeignKeyConstraint(["turno_id"], [f"{SCHEMA}.turnos.id"], ondelete="RESTRICT",
                                 name="fk_remanejamentos_turno"),
        sa.ForeignKeyConstraint(["tpa_out_id"], [f"{SCHEMA}.tpas.id"], ondelete="RESTRICT",
                                 name="fk_remanejamentos_tpa_out"),
        sa.ForeignKeyConstraint(["tpa_in_id"], [f"{SCHEMA}.tpas.id"], ondelete="RESTRICT",
                                 name="fk_remanejamentos_tpa_in"),
        sa.ForeignKeyConstraint(["funcao_origem_id"], [f"{SCHEMA}.funcoes.id"], ondelete="RESTRICT",
                                 name="fk_remanejamentos_funcao"),
        sa.ForeignKeyConstraint(["faina_origem_id"], [f"{SCHEMA}.fainas.id"], ondelete="RESTRICT",
                                 name="fk_remanejamentos_faina"),
        sa.ForeignKeyConstraint(["base_legal_cct_id"], [f"{SCHEMA}.cct_clausulas.id"],
                                 ondelete="RESTRICT", name="fk_remanejamentos_cct"),
        sa.ForeignKeyConstraint(["fiscal_id"], [f"{SCHEMA}.fiscais.id"], ondelete="RESTRICT",
                                 name="fk_remanejamentos_fiscal"),
        sa.ForeignKeyConstraint(["hash_anterior_id"], [f"{SCHEMA}.remanejamentos.id"],
                                 ondelete="SET NULL", name="fk_remanejamentos_hash_anterior"),
        sa.UniqueConstraint("codigo_se", name="uq_remanejamentos_codigo_se"),
        sa.CheckConstraint(
            "(motivo <> 'OUTRO') OR (motivo_outro_texto IS NOT NULL)",
            name="ck_remanejamentos_motivo_outro",
        ),
        sa.CheckConstraint(
            "(base_legal_cct_id IS NOT NULL) OR (base_legal_texto_livre IS NOT NULL)",
            name="ck_remanejamentos_base_legal",
        ),
        sa.CheckConstraint(
            "(status NOT IN ('ACK','NACK')) OR (ack_at IS NOT NULL)",
            name="ck_remanejamentos_ack_status",
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_remanejamentos_snapshot", "remanejamentos", ["snapshot_origem_id"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_data", "remanejamentos", ["data_referencia"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_tpa_out", "remanejamentos", ["tpa_out_id"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_tpa_in", "remanejamentos", ["tpa_in_id"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_motivo", "remanejamentos", ["motivo"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_cct", "remanejamentos", ["base_legal_cct_id"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_fiscal", "remanejamentos", ["fiscal_id"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_status", "remanejamentos", ["status"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_hash", "remanejamentos", ["hash_evento"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_hash_anterior", "remanejamentos", ["hash_anterior_id"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_created", "remanejamentos", ["created_at"], schema=SCHEMA)
    op.create_index("idx_remanejamentos_purge_after", "remanejamentos", ["purge_after"], schema=SCHEMA)
    op.create_index(
        "idx_remanejamentos_deleted_at", "remanejamentos", ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"), schema=SCHEMA,
    )

    # Trigger BEFORE INSERT: gera codigo_se automaticamente
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS lousa_main.remanejamentos_codigo_se_seq;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION lousa_main.fn_remanejamentos_codigo_se()
        RETURNS TRIGGER AS $$
        DECLARE
            v_ymd TEXT;
            v_seq INT;
            v_codigo TEXT;
        BEGIN
            v_ymd := to_char(NEW.created_at, 'YYYYMMDD');
            -- Sequência diária: usar offset derivado de data para garantir
            -- reinício por dia. Solução simples: row_number diário.
            SELECT COALESCE(MAX(
                CAST(substring(codigo_se FROM '\\d{3}$') AS INT)
            ), 0) + 1
            INTO v_seq
            FROM lousa_main.remanejamentos
            WHERE codigo_se LIKE 'SE-' || v_ymd || '-%';
            v_codigo := 'SE-' || v_ymd || '-' || lpad(v_seq::TEXT, 3, '0');
            NEW.codigo_se := v_codigo;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER tg_remanejamentos_codigo_se
        BEFORE INSERT ON lousa_main.remanejamentos
        FOR EACH ROW
        WHEN (NEW.codigo_se IS NULL OR NEW.codigo_se = '')
        EXECUTE FUNCTION lousa_main.fn_remanejamentos_codigo_se();
    """)

    # ---- remanejamento_historico (DD v1 §3.15) — append-only
    op.create_table(
        "remanejamento_historico",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("remanejamento_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status_anterior", postgresql.ENUM(name="status_remanejamento_enum", create_type=False),
                  nullable=True),
        sa.Column("status_novo", postgresql.ENUM(name="status_remanejamento_enum", create_type=False),
                  nullable=False),
        sa.Column("motivo_transicao", sa.Text, nullable=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_origem", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["remanejamento_id"], [f"{SCHEMA}.remanejamentos.id"],
                                 ondelete="RESTRICT", name="fk_reman_hist_remanejamento"),
        sa.ForeignKeyConstraint(["usuario_id"], [f"{SCHEMA}.users.id"],
                                 ondelete="RESTRICT", name="fk_reman_hist_usuario"),
        schema=SCHEMA,
    )
    op.create_index("idx_reman_hist_remanejamento_created", "remanejamento_historico",
                    ["remanejamento_id", "created_at"], schema=SCHEMA)
    # Trigger append-only
    op.execute("""
        CREATE OR REPLACE FUNCTION lousa_main.fn_block_update_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'TABELA_IMUTAVEL: % não aceita %', TG_TABLE_NAME, TG_OP
                USING ERRCODE = '23000';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER tg_reman_hist_block_update
        BEFORE UPDATE ON lousa_main.remanejamento_historico
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)
    op.execute("""
        CREATE TRIGGER tg_reman_hist_block_delete
        BEFORE DELETE ON lousa_main.remanejamento_historico
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)

    # =========================================================================
    # 8. INTEGRAÇÃO OGMO (DD v1 §3.16, §3.17)
    # =========================================================================

    # ---- ogmo_webhook_endpoints (DD v1 §3.17) — antes de ogmo_notificacoes (FK)
    op.create_table(
        "ogmo_webhook_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("porto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        # TODO(D10): secret_hmac criptografado (pgcrypto ou KMS)?
        sa.Column("secret_hmac", sa.Text, nullable=False),
        sa.Column("eventos_assinados", postgresql.ARRAY(sa.Text), nullable=False,
                  server_default=sa.text("ARRAY['remanejamento.criado','remanejamento.atualizado']")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("ultimo_ping_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_ping_status", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["porto_id"], [f"{SCHEMA}.portos.id"], ondelete="RESTRICT",
                                 name="fk_ogmo_webhook_porto"),
        schema=SCHEMA,
    )

    # ---- ogmo_notificacoes (DD v1 §3.16)
    op.create_table(
        "ogmo_notificacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("remanejamento_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canal", postgresql.ENUM(name="canal_notificacao_enum", create_type=False), nullable=False),
        sa.Column("template_id", sa.Text, nullable=False),
        sa.Column("assunto", sa.Text, nullable=True),
        sa.Column("payload_json", postgresql.JSONB, nullable=False),
        sa.Column("payload_hash_sha256", sa.CHAR(64), nullable=False),
        sa.Column("destinatario_email", sa.Text, nullable=True),
        sa.Column("destinatario_webhook_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_message_id", sa.Text, nullable=True),
        sa.Column("status", postgresql.ENUM(name="status_notificacao_enum", create_type=False),
                  nullable=False, server_default=sa.text("'PENDENTE'::status_notificacao_enum")),
        sa.Column("tentativas", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("proxima_tentativa_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enviado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entregue_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("falhou_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("erro_detalhes", sa.Text, nullable=True),
        sa.Column("pdf_anexo_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + INTERVAL '5 years'")),
        sa.ForeignKeyConstraint(["remanejamento_id"], [f"{SCHEMA}.remanejamentos.id"],
                                 ondelete="RESTRICT", name="fk_ogmo_notif_remanejamento"),
        sa.ForeignKeyConstraint(["destinatario_webhook_id"],
                                 [f"{SCHEMA}.ogmo_webhook_endpoints.id"], ondelete="SET NULL",
                                 name="fk_ogmo_notif_webhook"),
        sa.CheckConstraint(
            "(canal = 'EMAIL' AND destinatario_email IS NOT NULL) "
            "OR (canal = 'WEBHOOK' AND destinatario_webhook_id IS NOT NULL) "
            "OR (canal = 'PAINEL_OGMO')",
            name="ck_ogmo_notif_destinatario",
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_ogmo_notif_remanejamento", "ogmo_notificacoes", ["remanejamento_id"], schema=SCHEMA)
    op.create_index("idx_ogmo_notif_canal", "ogmo_notificacoes", ["canal"], schema=SCHEMA)
    op.create_index(
        "idx_ogmo_notif_payload_gin", "ogmo_notificacoes", ["payload_json"],
        postgresql_using="gin", schema=SCHEMA,
    )
    op.create_index("idx_ogmo_notif_hash", "ogmo_notificacoes", ["payload_hash_sha256"], schema=SCHEMA)
    op.create_index("idx_ogmo_notif_provider_id", "ogmo_notificacoes", ["provider_message_id"], schema=SCHEMA)
    op.create_index("idx_ogmo_notif_status", "ogmo_notificacoes", ["status"], schema=SCHEMA)
    op.create_index("idx_ogmo_notif_proxima_tentativa", "ogmo_notificacoes", ["proxima_tentativa_em"], schema=SCHEMA)

    # =========================================================================
    # 9. TPA OPERAÇÃO (DD v1 §3.18)
    # =========================================================================

    op.create_table(
        "tpa_confirmacoes_presenca",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tpa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lousa_cell_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data_referencia", sa.Date, nullable=False),
        sa.Column("turno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confirmou", sa.Boolean, nullable=False),
        sa.Column("confirmado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("precisao_m", sa.Integer, nullable=True),
        sa.Column("dispositivo", sa.Text, nullable=True),
        sa.Column("hash_integridade", sa.CHAR(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + INTERVAL '24 months'")),
        sa.ForeignKeyConstraint(["tpa_id"], [f"{SCHEMA}.tpas.id"], ondelete="RESTRICT",
                                 name="fk_confirm_tpa"),
        sa.ForeignKeyConstraint(["lousa_cell_id"], [f"{SCHEMA}.lousa_cells.id"], ondelete="SET NULL",
                                 name="fk_confirm_lousa_cell"),
        sa.ForeignKeyConstraint(["turno_id"], [f"{SCHEMA}.turnos.id"], ondelete="RESTRICT",
                                 name="fk_confirm_turno"),
        sa.UniqueConstraint("tpa_id", "data_referencia", "turno_id", name="uq_confirm_tpa_data_turno"),
        sa.CheckConstraint(
            "(latitude IS NULL) OR (latitude BETWEEN -90 AND 90)",
            name="ck_confirm_coordenadas",
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_confirm_tpa_data", "tpa_confirmacoes_presenca",
                    ["tpa_id", "data_referencia"], schema=SCHEMA)
    op.create_index("idx_confirm_hash", "tpa_confirmacoes_presenca", ["hash_integridade"], schema=SCHEMA)
    op.create_index(
        "idx_confirm_deleted_at", "tpa_confirmacoes_presenca", ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"), schema=SCHEMA,
    )

    # =========================================================================
    # 10. LGPD (DD v1 §3.19, §3.23, §3.24)
    # =========================================================================

    # ---- termos_consentimento (DD v1 §3.19) — append-only
    op.create_table(
        "termos_consentimento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tpa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("versao_termo", sa.Text, nullable=False),
        sa.Column("aceito", sa.Boolean, nullable=False),
        sa.Column("aceito_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ip_origem", postgresql.INET, nullable=False),
        sa.Column("user_agent", sa.Text, nullable=False),
        sa.Column("metodo", postgresql.ENUM(name="termo_metodo_enum", create_type=False), nullable=False),
        sa.Column("termo_texto_hash", sa.CHAR(64), nullable=False),
        sa.Column("termo_url_pdf", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tpa_id"], [f"{SCHEMA}.tpas.id"], ondelete="RESTRICT",
                                 name="fk_termos_tpa"),
        schema=SCHEMA,
    )
    op.create_index("idx_termos_tpa_created", "termos_consentimento", ["tpa_id", "created_at"], schema=SCHEMA)
    op.create_index("idx_termos_versao", "termos_consentimento", ["versao_termo"], schema=SCHEMA)
    op.execute("""
        CREATE TRIGGER tg_termos_block_update
        BEFORE UPDATE ON lousa_main.termos_consentimento
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)
    op.execute("""
        CREATE TRIGGER tg_termos_block_delete
        BEFORE DELETE ON lousa_main.termos_consentimento
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)

    # ---- lgpd_solicitacoes (DD v1 §3.23)
    op.create_table(
        "lgpd_solicitacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("protocolo", sa.Text, nullable=False),
        sa.Column("tpa_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", postgresql.ENUM(name="lgpd_tipo_enum", create_type=False), nullable=False),
        sa.Column("descricao", sa.Text, nullable=True),
        sa.Column("status", postgresql.ENUM(name="lgpd_status_enum", create_type=False),
                  nullable=False, server_default=sa.text("'RECEBIDA'::lgpd_status_enum")),
        sa.Column("prazo_resposta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recebida_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("respondida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resposta_texto", sa.Text, nullable=True),
        sa.Column("documentos_anexos_url", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("responsavel_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now() + INTERVAL '5 years'")),
        sa.ForeignKeyConstraint(["tpa_id"], [f"{SCHEMA}.tpas.id"], ondelete="RESTRICT",
                                 name="fk_lgpd_tpa"),
        sa.ForeignKeyConstraint(["responsavel_user_id"], [f"{SCHEMA}.users.id"],
                                 ondelete="RESTRICT", name="fk_lgpd_responsavel"),
        sa.UniqueConstraint("protocolo", name="uq_lgpd_protocolo"),
        sa.CheckConstraint(
            "(executada_em IS NULL) OR (status = 'EXECUTADA')",
            name="ck_lgpd_executada_status",
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_lgpd_tpa", "lgpd_solicitacoes", ["tpa_id"], schema=SCHEMA)
    op.create_index("idx_lgpd_tipo", "lgpd_solicitacoes", ["tipo"], schema=SCHEMA)
    op.create_index("idx_lgpd_status", "lgpd_solicitacoes", ["status"], schema=SCHEMA)
    op.create_index("idx_lgpd_prazo", "lgpd_solicitacoes", ["prazo_resposta"], schema=SCHEMA)
    op.create_index("idx_lgpd_purge_after", "lgpd_solicitacoes", ["purge_after"], schema=SCHEMA)
    # Trigger BEFORE INSERT: gera protocolo + prazo_resposta (15 dias Art. 18 §5º)
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS lousa_main.lgpd_solicitacoes_protocolo_seq;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION lousa_main.fn_lgpd_solicitacao_defaults()
        RETURNS TRIGGER AS $$
        DECLARE
            v_seq INT;
            v_ano TEXT;
        BEGIN
            IF NEW.protocolo IS NULL OR NEW.protocolo = '' THEN
                v_seq := nextval('lousa_main.lgpd_solicitacoes_protocolo_seq');
                v_ano := to_char(NEW.recebida_em, 'YYYY');
                NEW.protocolo := 'LGPD-' || v_ano || '-' || lpad(v_seq::TEXT, 4, '0');
            END IF;
            IF NEW.prazo_resposta IS NULL THEN
                NEW.prazo_resposta := NEW.recebida_em + INTERVAL '15 days';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER tg_lgpd_defaults
        BEFORE INSERT ON lousa_main.lgpd_solicitacoes
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_lgpd_solicitacao_defaults();
    """)

    # ---- lgpd_purge_log (DD v1 §3.24) — append-only
    op.create_table(
        "lgpd_purge_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("executado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tabela_origem", sa.Text, nullable=False),
        sa.Column("registros_deletados", sa.Integer, nullable=False),
        sa.Column("criterio", sa.Text, nullable=False),
        sa.Column("registros_ids_antes_delete", postgresql.JSONB, nullable=False),
        sa.Column("hash_lote_sha256", sa.CHAR(64), nullable=False),
        sa.Column("job_id", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema=SCHEMA,
    )
    op.create_index("idx_purge_log_executado", "lgpd_purge_log", ["executado_em"], schema=SCHEMA)
    op.create_index("idx_purge_log_tabela", "lgpd_purge_log", ["tabela_origem"], schema=SCHEMA)
    op.create_index(
        "idx_purge_log_ids_gin", "lgpd_purge_log", ["registros_ids_antes_delete"],
        postgresql_using="gin", schema=SCHEMA,
    )
    op.execute("""
        CREATE TRIGGER tg_purge_log_block_update
        BEFORE UPDATE ON lousa_main.lgpd_purge_log
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)
    op.execute("""
        CREATE TRIGGER tg_purge_log_block_delete
        BEFORE DELETE ON lousa_main.lgpd_purge_log
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)

    # =========================================================================
    # 11. AUDITORIA (DD v1 §3.20, §3.21, §3.22)
    # =========================================================================

    # ---- audit_events (DD v1 §3.20) — sequência + append-only
    # Sequence dedicada para `sequencia` (criada ANTES da tabela).
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS lousa_main.audit_events_sequencia_seq;
    """)
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("sequencia", sa.BigInteger, nullable=False,
                  server_default=sa.text("nextval('lousa_main.audit_events_sequencia_seq')")),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.Text, nullable=True),
        sa.Column("actor_ip", postgresql.INET, nullable=True),
        sa.Column("actor_user_agent", sa.Text, nullable=True),
        sa.Column("payload_before", postgresql.JSONB, nullable=True),
        sa.Column("payload_after", postgresql.JSONB, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("hash_anterior", sa.CHAR(64), nullable=True),
        sa.Column("hash_evento", sa.CHAR(64), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["actor_user_id"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT",
                                 name="fk_audit_actor"),
        sa.UniqueConstraint("sequencia", name="uq_audit_events_sequencia"),
        sa.UniqueConstraint("hash_evento", name="uq_audit_events_hash"),
        sa.CheckConstraint(
            "(event_type <> 'UPDATE') OR (payload_before IS NOT NULL)",
            name="ck_audit_payload_consistent",
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_audit_entity", "audit_events", ["entity_type"], schema=SCHEMA)
    op.create_index(
        "idx_audit_entity_entity_id_created", "audit_events",
        ["entity_type", "entity_id", "criado_em"], schema=SCHEMA,
    )
    op.create_index("idx_audit_actor", "audit_events", ["actor_user_id"], schema=SCHEMA)
    op.create_index(
        "idx_audit_actor_created", "audit_events", ["actor_user_id", "criado_em"], schema=SCHEMA,
    )
    op.create_index("idx_audit_event_type", "audit_events", ["event_type"], schema=SCHEMA)
    op.create_index(
        "idx_audit_event_type_created", "audit_events", ["event_type", "criado_em"], schema=SCHEMA,
    )
    op.create_index(
        "idx_audit_payload_gin", "audit_events", ["payload_after"],
        postgresql_using="gin", schema=SCHEMA,
    )
    op.create_index("idx_audit_criado_em", "audit_events", ["criado_em"], schema=SCHEMA)
    op.execute("""
        CREATE TRIGGER tg_audit_block_update
        BEFORE UPDATE ON lousa_main.audit_events
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)
    op.execute("""
        CREATE TRIGGER tg_audit_block_delete
        BEFORE DELETE ON lousa_main.audit_events
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)

    # ---- hash_chain_checkpoint (DD v1 §3.21)
    op.create_table(
        "hash_chain_checkpoint",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("executado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("executado_por", sa.Text, nullable=False),
        sa.Column("total_eventos_verificados", sa.BigInteger, nullable=False),
        sa.Column("primeiro_sequencia", sa.BigInteger, nullable=False),
        sa.Column("ultimo_sequencia", sa.BigInteger, nullable=False),
        sa.Column("hash_calculado_final", sa.CHAR(64), nullable=False),
        sa.Column("hash_esperado_final", sa.CHAR(64), nullable=False),
        sa.Column("integro", sa.Boolean, nullable=False),
        sa.Column("primeiro_evento_com_falha", sa.BigInteger, nullable=True),
        sa.Column("duracao_ms", sa.Integer, nullable=False),
        sa.Column("alerta_enviado", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("executado_em", name="uq_hash_checkpoint_executado"),
        schema=SCHEMA,
    )
    op.create_index("idx_hash_checkpoint_integro", "hash_chain_checkpoint", ["integro"], schema=SCHEMA)

    # ---- access_log (DD v1 §3.22) — append-only
    op.create_table(
        "access_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recurso_tipo", sa.Text, nullable=False),
        sa.Column("recurso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operacao", sa.Text, nullable=False),
        sa.Column("contexto", sa.Text, nullable=True),
        sa.Column("ip_origem", postgresql.INET, nullable=False),
        sa.Column("user_agent", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT",
                                 name="fk_access_log_user"),
        schema=SCHEMA,
    )
    op.create_index("idx_access_log_user_created", "access_log", ["user_id", "created_at"], schema=SCHEMA)
    op.create_index("idx_access_log_recurso", "access_log", ["recurso_tipo"], schema=SCHEMA)
    op.create_index(
        "idx_access_log_recurso_id", "access_log", ["recurso_tipo", "recurso_id"], schema=SCHEMA,
    )
    op.create_index("idx_access_log_operacao", "access_log", ["operacao"], schema=SCHEMA)
    op.execute("""
        CREATE TRIGGER tg_access_log_block_update
        BEFORE UPDATE ON lousa_main.access_log
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)
    op.execute("""
        CREATE TRIGGER tg_access_log_block_delete
        BEFORE DELETE ON lousa_main.access_log
        FOR EACH ROW EXECUTE FUNCTION lousa_main.fn_block_update_delete();
    """)


def downgrade() -> None:
    """Forward-only por convenção do projeto. Downgrade explícito
    deve ser uma migration reversa separada.
    """
    raise NotImplementedError(
        "Forward-only convention. Crie uma migration reversa explícita."
    )


# -----------------------------------------------------------------------------
# NOTA SOBRE O NÚMERO DE TABELAS
# -----------------------------------------------------------------------------
# O DD v1 declara 26 tabelas (sumário executivo §7) mas o §3 lista 25
# entradas reais (1-26 com `roles` = enum, não tabela; 25 efetivas).
# O ER textual mostra 26 caixas porque inclui `roles` na contagem visual.
#
# Esta migration cria as 25 tabelas que existem de fato conforme §3. Se
# Paulo confirmar que quer 26 com uma tabela `roles` (improvável — DD
# §3.2 diz "decisão consciente" de manter como enum), é trivial
# adicionar via migration 0002.
# -----------------------------------------------------------------------------
