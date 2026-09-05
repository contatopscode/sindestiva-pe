"""SINDESTIVA-PE · Models `Modulo` + `UsuarioModulo` (issue #14).

Gestão de usuários por MÓDULO do sistema.

O que é um "módulo" aqui (risco levantado no plano — "feature vs
bounded context"): é uma **área funcional navegável** do Centro de
Comando, 1:1 com um grupo de rotas da API e um item de sidebar do web
(`lousa`, `remanejamentos`, `ogmo`, `auditoria`, `bi`, `lgpd`, `tpa`,
`admin`). NÃO é bounded context de domínio nem tabela — é a unidade que
o Presidente enxerga quando diz "o Manoel só mexe na lousa".

Relação com o RBAC existente:
  - `users.role` (RoleEnum) continua sendo QUEM a pessoa é
    (FISCAL/DIRIGENTE/TPA) e segue governando o login.
  - `usuario_modulos.papel` (ModuloPapelEnum) é O QUE ela pode fazer
    em cada módulo. Ortogonal, aditivo — nenhum guard existente
    (ex.: `_require_dirigente` do /bi) muda de comportamento.
  - DIRIGENTE é superusuário: acessa todo módulo sem atribuição
    explícita (ver `app.core.permissions.is_superusuario`).

LGPD: `usuario_modulos` NÃO guarda dado pessoal — só o vínculo
(user_id, modulo_id, papel). Retenção segue o `users` pai via FK
CASCADE.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ModuloPapelEnum, pg_enum

# Tamanho máximo do slug — espelhado no `ModuloCreate` (Pydantic) e no
# VARCHAR(64) da migration 0004.
SLUG_MAX_LEN = 64


# ---------------------------------------------------------------------------
# Modulo
# ---------------------------------------------------------------------------


class Modulo(Base, TimestampMixin):
    """Área funcional do sistema (unidade de permissão).

    Volume esperado: ~10 linhas (uma por item de sidebar). Sem soft
    delete: "desativar" é `ativo=False`, que preserva as atribuições
    (reativar devolve os acessos como estavam) e mantém a FK dos
    vínculos íntegra.
    """

    __tablename__ = "modulos"
    __table_args__ = (
        Index("idx_modulos_ativo", "ativo"),
        Index("idx_modulos_ordem", "ordem"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    # Chave funcional usada pela policy (`requer_modulo("lousa")`).
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ordem de exibição na sidebar / matriz.
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("100"))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    atribuicoes: Mapped[list["UsuarioModulo"]] = relationship(
        "UsuarioModulo",
        back_populates="modulo",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __mapper_args__ = {"eager_defaults": True}


# ---------------------------------------------------------------------------
# UsuarioModulo
# ---------------------------------------------------------------------------


class UsuarioModulo(Base, TimestampMixin):
    """Vínculo User ↔ Módulo com papel (tabela de junção com atributo).

    Volume esperado: ~10 fiscais/dirigentes × ~8 módulos = ~80 linhas.
    TPAs não recebem atribuição (usam o PWA, não o Centro de Comando).

    `ondelete="CASCADE"` em ambas as FKs: o vínculo não tem valor
    isolado — sem o user ou sem o módulo, ele é lixo. Difere do
    `RESTRICT` usado em `tpas.user_id` porque lá o dado é histórico
    trabalhista (não pode sumir); aqui é só configuração de acesso.
    """

    __tablename__ = "usuario_modulos"
    __table_args__ = (
        UniqueConstraint("user_id", "modulo_id", name="uq_usuario_modulos_user_modulo"),
        Index("idx_usuario_modulos_user", "user_id"),
        Index("idx_usuario_modulos_modulo", "modulo_id"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    modulo_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.modulos.id", ondelete="CASCADE"),
        nullable=False,
    )

    papel: Mapped[ModuloPapelEnum] = mapped_column(
        pg_enum(ModuloPapelEnum),
        nullable=False,
        server_default=text("'VISUALIZAR'::modulo_papel_enum"),
    )

    # Quem concedeu (trilha mínima; auditoria completa fica em
    # `audit_events`, fora do escopo desta issue).
    concedido_por: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="SET NULL"),
        nullable=True,
    )

    modulo: Mapped[Modulo] = relationship(
        "Modulo", back_populates="atribuicoes", lazy="joined"
    )

    __mapper_args__ = {"eager_defaults": True}


__all__ = ["Modulo", "UsuarioModulo", "SLUG_MAX_LEN"]
