"""SINDESTIVA-PE · Model `User` (auth unificada) + perfis TPA.

DD v1 §3.1 (users) + §3.3 (tpas).

`User` é a base de auth (NextAuth v5). Perfis de negócio (`Tpa`,
`Fiscal`, `Dirigente`) ficam em arquivos separados para reduzir
colisão em migração e melhorar legibilidade — `Tpa` aqui porque
compartilha 1:1 com User onde role=TPA, e mantém o arquivo `users.py`
focado em auth.

TODO(D1): TPA pode ter password_hash ou só OTP? Recomendação SINDESTIVA
Bot = (a) só OTP. A constraint `ck_users_password_for_non_tpa` foi
incluída no DD como padrão conservador; remover se Paulo confirmar
opção (b).

TODO(D3): volume real de TPAs (Suape + Recife). DD v1 §5 assume 2.000
alinhado com a persona do plano. Manoel Costa confirma em K-3
(visita a Suape). Sem impacto de schema — só ajuste de expectativa
para índices de busca e tamanho de tabela.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import CHAR

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import RoleEnum, TpaStatusEnum, UserStatusEnum, pg_enum

if TYPE_CHECKING:
    from app.models.perfis_internos import Dirigente, Fiscal


# ---------------------------------------------------------------------------
# User (DD v1 §3.1)
# ---------------------------------------------------------------------------

class User(Base, TimestampMixin, SoftDeleteMixin):
    """Auth unificada de fiscais, dirigentes e TPAs (NextAuth v5).

    Volume esperado: ~2.020 linhas (10 fiscais + 10 dirigentes + ~2.000 TPAs).
    LGPD: sim (e-mail + telefone + flag de aceite).
    Retenção: 24m após `deleted_at` (default `SoftDeleteMixin`).
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_role", "role"),
        Index("idx_users_status", "status"),
        Index("idx_users_created_at", "created_at"),
        Index("idx_users_deleted_at", "deleted_at", postgresql_where=text("deleted_at IS NULL")),
        Index("idx_users_purge_after", "purge_after"),
        Index("idx_users_telefone", "telefone"),
        # CHECK constraints são criadas na migration (DD v1 §3.1).
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    email: Mapped[str | None] = mapped_column(CITEXT(), nullable=True)
    telefone: Mapped[str | None] = mapped_column(Text, nullable=True)

    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    role: Mapped[RoleEnum] = mapped_column(
        pg_enum(RoleEnum),
        nullable=False,
    )
    status: Mapped[UserStatusEnum] = mapped_column(
        pg_enum(UserStatusEnum),
        nullable=False,
        server_default=text("'PENDENTE_ACEITE'::user_status_enum"),
    )

    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    last_login_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_terms_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relacionamentos 1:1 com perfis de negócio (lazy="selectin" pra
    # async; carrega o perfil automaticamente no SELECT).
    tpa: Mapped["Tpa | None"] = relationship(
        "Tpa",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="save-update, merge",
    )
    fiscal: Mapped["Fiscal | None"] = relationship(
        "Fiscal",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="save-update, merge",
    )
    dirigente: Mapped["Dirigente | None"] = relationship(
        "Dirigente",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="save-update, merge",
    )

    __mapper_args__ = {
        "eager_defaults": True,
    }


# ---------------------------------------------------------------------------
# Tpa (DD v1 §3.3)
# ---------------------------------------------------------------------------

class Tpa(Base, TimestampMixin, SoftDeleteMixin):
    """Perfil de negócio do Trabalhador Portuário Avulso (1:1 com User).

    Cruzar matrículas OGMO com cadastro interno do Sindicato (T2-05 do
    plano). `categoria` é denormalizado de `funcoes` para o BI
    ("Taxa comparecimento por categoria", Sprint 7).
    """

    __tablename__ = "tpas"
    __table_args__ = (
        Index("idx_tpas_nome_trgm", "nome_completo", postgresql_using="gin",
              postgresql_ops={"nome_completo": "gin_trgm_ops"}),
        Index("idx_tpas_funcao_base", "funcao_base_id"),
        Index("idx_tpas_categoria", "categoria"),
        Index("idx_tpas_status_cadastro", "status_cadastro"),
        Index("idx_tpas_data_desligamento", "data_desligamento"),
        Index("idx_tpas_telefone", "telefone"),
        Index("idx_tpas_purge_after", "purge_after"),
        Index("idx_tpas_deleted_at", "deleted_at", postgresql_where=text("deleted_at IS NULL")),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    cpf: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    nome_completo: Mapped[str] = mapped_column(Text, nullable=False)
    matricula_ogmo: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    telefone: Mapped[str] = mapped_column(Text, nullable=False)

    funcao_base_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.funcoes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    categoria: Mapped[str] = mapped_column(Text, nullable=False)

    status_cadastro: Mapped[TpaStatusEnum] = mapped_column(
        pg_enum(TpaStatusEnum),
        nullable=False,
        server_default=text("'ATIVO'::tpa_status_enum"),
    )

    data_admissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_desligamento: Mapped[date | None] = mapped_column(Date, nullable=True)

    consentimento_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consentimento_versao: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="tpa", lazy="joined")


__all__ = ["User", "Tpa"]
