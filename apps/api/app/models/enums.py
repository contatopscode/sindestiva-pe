"""SINDESTIVA-PE · Enums de domínio.

Mapeamento direto com o DD v1 §3. Postgres recebe `native_enum=True`
(ENUM nativo) — mais rígido e indexável que `text + CHECK`.

Convenção de nome: `snake_case` em Python, valor em MAIÚSCULAS. O nome
do tipo Postgres é `snake_case` em lowercase, ex: `RoleEnum` →
`role_enum` (controlado via `name=` no campo).

Helper `pg_enum()`: converte o `Enum` Python em `sqlalchemy.Enum` com
`native_enum=True`, `name=` e schema `lousa_main`. SEM esse wrapper, o
SQLAlchemy 2 não consegue mapear RoleEnum (Python) ↔ role_enum (Postgres)
e quebra em runtime + Alembic autogenerate.
"""
from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects import postgresql


# Schema default do MVP (DD v1 ADR-002 — schema único).
SCHEMA = "lousa_main"


def pg_enum(python_enum: type[enum.Enum]) -> SAEnum:
    """Converte um `enum.Enum` Python em `sqlalchemy.Enum` Postgres-native.

    Garante:
      - `native_enum=True` (ENUM nativo, não CHECK)
      - `name=` em snake_case (mesmo do tipo criado na migration 0001)
      - `schema=lousa_main` (single-schema do MVP)
      - `create_type=False` (a migration já cria; evita conflito em
        autogenerate)

    Uso:
        role: Mapped[RoleEnum] = mapped_column(
            pg_enum(RoleEnum), nullable=False
        )
    """
    # Extrai nome da classe (RoleEnum → role_enum)
    name = "".join(
        ["_" + c.lower() if c.isupper() else c for c in python_enum.__name__]
    ).lstrip("_")
    # Normaliza: "UserStatusEnum" → "user_status_enum"
    parts = name.split("_")
    normalized = "_".join(parts[:-1] + ["enum"]) if parts[-1] != "enum" else name
    return postgresql.ENUM(
        *[m.value for m in python_enum],
        name=normalized,
        schema=SCHEMA,
        create_type=False,
        native_enum=True,
    )


# ---------------------------------------------------------------------------
# Auth / RBAC (DD v1 §3.1, §3.2)
# ---------------------------------------------------------------------------

class RoleEnum(str, enum.Enum):
    """3 roles no MVP. RBAC detalhado fica em `packages/shared/rbac.ts`."""

    FISCAL = "FISCAL"
    DIRIGENTE = "DIRIGENTE"
    TPA = "TPA"


class UserStatusEnum(str, enum.Enum):
    """Ciclo de vida de um User."""

    PENDENTE_ACEITE = "PENDENTE_ACEITE"
    ATIVO = "ATIVO"
    BLOQUEADO = "BLOQUEADO"
    INATIVO = "INATIVO"


# ---------------------------------------------------------------------------
# Perfis de negócio (DD v1 §3.3, §3.4, §3.5)
# ---------------------------------------------------------------------------

class TpaStatusEnum(str, enum.Enum):
    ATIVO = "ATIVO"
    AFASTADO = "AFASTADO"
    DESLIGADO = "DESLIGADO"
    SUSPENSO = "SUSPENSO"


class FiscalStatusEnum(str, enum.Enum):
    ATIVO = "ATIVO"
    AFASTADO = "AFASTADO"
    DESLIGADO = "DESLIGADO"


# ---------------------------------------------------------------------------
# Lousa (DD v1 §3.12, §3.13)
# ---------------------------------------------------------------------------

class SnapshotStatusEnum(str, enum.Enum):
    OK = "OK"
    PARCIAL = "PARCIAL"
    ERRO = "ERRO"
    LAYOUT_MUDOU = "LAYOUT_MUDOU"


class CellStatusEnum(str, enum.Enum):
    NORMAL = "NORMAL"
    AUSENTE = "AUSENTE"
    REMANEJADO = "REMANEJADO"
    CONFIRMADO = "CONFIRMADO"


# ---------------------------------------------------------------------------
# Remanejamento (DD v1 §3.14, §3.15)
# ---------------------------------------------------------------------------

class MotivoRemanejamentoEnum(str, enum.Enum):
    ATESTADO_MEDICO = "ATESTADO_MEDICO"
    FALTA_INJUSTIFICADA = "FALTA_INJUSTIFICADA"
    REFORCO_TERNO = "REFORCO_TERNO"
    TROCA_TURNO = "TROCA_TURNO"
    ATRASO_15MIN = "ATRASO_15MIN"
    FALTA_EPI = "FALTA_EPI"
    LIBERACAO_ANTECIPADA = "LIBERACAO_ANTECIPADA"
    OUTRO = "OUTRO"


class StatusRemanejamentoEnum(str, enum.Enum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    NOTIFICADO_OGMO = "NOTIFICADO_OGMO"
    ACK = "ACK"
    NACK = "NACK"
    CANCELADO = "CANCELADO"


# ---------------------------------------------------------------------------
# Notificação OGMO (DD v1 §3.16, §3.17)
# ---------------------------------------------------------------------------

class CanalNotificacaoEnum(str, enum.Enum):
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"
    PAINEL_OGMO = "PAINEL_OGMO"


class StatusNotificacaoEnum(str, enum.Enum):
    PENDENTE = "PENDENTE"
    ENVIADO = "ENVIADO"
    ENTREGUE = "ENTREGUE"
    FALHOU = "FALHOU"
    REJEITADO = "REJEITADO"


# ---------------------------------------------------------------------------
# LGPD (DD v1 §3.19, §3.23)
# ---------------------------------------------------------------------------

class TermoMetodoEnum(str, enum.Enum):
    PRIMEIRO_LOGIN = "PRIMEIRO_LOGIN"
    RECONFIRMACAO = "RECONFIRMACAO"
    ALTERACAO_TERMO = "ALTERACAO_TERMO"
    REVOGACAO = "REVOGACAO"


class LgpdTipoEnum(str, enum.Enum):
    EXCLUSAO = "EXCLUSAO"
    PORTABILIDADE = "PORTABILIDADE"
    CORRECAO = "CORRECAO"
    CONFIRMACAO_EXISTENCIA = "CONFIRMACAO_EXISTENCIA"
    REVOGACAO_CONSENTIMENTO = "REVOGACAO_CONSENTIMENTO"


class LgpdStatusEnum(str, enum.Enum):
    RECEBIDA = "RECEBIDA"
    EM_ANALISE = "EM_ANALISE"
    DEFERIDA = "DEFERIDA"
    INDEFERIDA = "INDEFERIDA"
    EXECUTADA = "EXECUTADA"


# ---------------------------------------------------------------------------
# Funções portuárias (DD v1 §3.8) — `categoria`
# ---------------------------------------------------------------------------
# NOTA: `funcoes.categoria` é TEXT com CHECK constraint (DD v1 §3.8),
# NÃO enum nativo Postgres. A migration 0001 usa `ck_funcoes_categoria`
# em vez de `CREATE TYPE funcao_categoria_enum`. Por isso NÃO há
# `FuncaoCategoriaEnum` aqui — o domínio é validado pela CHECK e a
# coluna é `Mapped[str]` no model.

# ---------------------------------------------------------------------------
# TPA confirmação (DD v1 §3.18) — `operacao` boolean
# ---------------------------------------------------------------------------
# `tpa_confirmacoes_presenca.confirmou` é boolean, não enum. Mantido aqui
# só por completude de seção.

__all__ = [
    "pg_enum",
    "SCHEMA",
    # auth
    "RoleEnum",
    "UserStatusEnum",
    # perfis
    "TpaStatusEnum",
    "FiscalStatusEnum",
    # lousa
    "SnapshotStatusEnum",
    "CellStatusEnum",
    # remanejamento
    "MotivoRemanejamentoEnum",
    "StatusRemanejamentoEnum",
    # ogmo
    "CanalNotificacaoEnum",
    "StatusNotificacaoEnum",
    # lgpd
    "TermoMetodoEnum",
    "LgpdTipoEnum",
    "LgpdStatusEnum",
    # NOTA: FuncaoCategoriaEnum removido — categoria é TEXT com CHECK,
    # não enum nativo. Ver comentário no lugar original.
]
