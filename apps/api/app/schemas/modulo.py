"""SINDESTIVA-PE · Pydantic schemas — Módulos & permissões (issue #14)."""
from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ModuloPapelEnum

# Slug = chave funcional usada pela policy (`requer_modulo("lousa")`).
# Espelha `ck_modulos_slug_formato` na migration 0004.
SLUG_REGEX = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SLUG_MAX_LEN = 64


def _validar_slug(valor: str) -> str:
    """Normaliza (trim + lowercase) e valida o formato do slug."""
    normalizado = valor.strip().lower()
    if not SLUG_REGEX.match(normalizado):
        msg = (
            "slug deve ser lowercase alfanumérico com '-' ou '_' "
            f"(1..{SLUG_MAX_LEN} chars), sem espaços nem acentos."
        )
        raise ValueError(msg)
    return normalizado


# ---------------------------------------------------------------------------
# Módulo — entrada
# ---------------------------------------------------------------------------


class ModuloCreate(BaseModel):
    """POST /modulos."""

    slug: str = Field(description="Chave funcional (ex.: 'lousa').")
    nome: str = Field(min_length=1, max_length=120)
    descricao: str | None = Field(default=None, max_length=500)
    ordem: int = Field(default=100, ge=0, le=9999)
    ativo: bool = True

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        return _validar_slug(v)

    @field_validator("nome")
    @classmethod
    def _nome(cls, v: str) -> str:
        limpo = v.strip()
        if not limpo:
            msg = "nome não pode ser vazio."
            raise ValueError(msg)
        return limpo


class ModuloUpdate(BaseModel):
    """PATCH /modulos/{id} — todos os campos opcionais, mas ao menos um.

    `ativo=False` é a forma de DESATIVAR um módulo (critério de aceite).
    Não apagamos: as atribuições ficam preservadas para reativação.
    """

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    descricao: str | None = Field(default=None, max_length=500)
    ordem: int | None = Field(default=None, ge=0, le=9999)
    ativo: bool | None = None

    @model_validator(mode="after")
    def _ao_menos_um_campo(self) -> "ModuloUpdate":
        if all(
            getattr(self, campo) is None
            for campo in ("nome", "descricao", "ordem", "ativo")
        ):
            msg = "informe ao menos um campo para atualizar."
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Módulo — saída
# ---------------------------------------------------------------------------


class ModuloOut(BaseModel):
    """Módulo como o admin vê (CRUD e matriz)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    nome: str
    descricao: str | None
    ordem: int
    ativo: bool
    created_at: datetime
    updated_at: datetime


class ModuloDoUsuarioOut(BaseModel):
    """Módulo como o usuário autenticado vê (GET /modulos).

    Inclui o `papel` efetivo — para DIRIGENTE (superusuário) vem ADMIN
    mesmo sem atribuição explícita.
    """

    id: UUID
    slug: str
    nome: str
    descricao: str | None
    ordem: int
    papel: ModuloPapelEnum


class ModulosDoUsuarioResponse(BaseModel):
    items: list[ModuloDoUsuarioOut]
    total: int = Field(ge=0)


class ModulosListResponse(BaseModel):
    items: list[ModuloOut]
    total: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Atribuição (user × módulo × papel)
# ---------------------------------------------------------------------------


class AtribuicaoCreate(BaseModel):
    """POST /modulos/atribuicoes — concede (ou atualiza) acesso."""

    user_id: UUID
    modulo_id: UUID
    papel: ModuloPapelEnum


class AtribuicaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    modulo_id: UUID
    papel: ModuloPapelEnum
    concedido_por: UUID | None
    created_at: datetime
    updated_at: datetime


class AcessoModuloOut(BaseModel):
    """GET /modulos/{id}/acesso — quem sou eu neste módulo.

    Existe para o frontend decidir o que renderizar (botão de editar,
    etc.) sem replicar a policy em TypeScript, e serve de rota-canário
    protegida nos testes E2E.
    """

    modulo_id: UUID
    slug: str
    papel: ModuloPapelEnum
    superusuario: bool


# ---------------------------------------------------------------------------
# Matriz de permissões (UI de admin)
# ---------------------------------------------------------------------------


class UsuarioMatrizOut(BaseModel):
    """Linha da matriz: um usuário e seus papéis por módulo."""

    id: UUID
    email: str | None
    nome: str | None
    role: str
    status: str
    # {slug_do_modulo: papel} — só atribuições explícitas. O bypass do
    # DIRIGENTE NÃO é materializado aqui: a matriz mostra o que foi
    # concedido, e a UI sinaliza o superusuário pelo `role`.
    papeis: dict[str, ModuloPapelEnum]


class MatrizPermissoesResponse(BaseModel):
    """GET /modulos/matriz — todos os usuários × todos os módulos."""

    modulos: list[ModuloOut]
    usuarios: list[UsuarioMatrizOut]
    total_usuarios: int = Field(ge=0)
    total_modulos: int = Field(ge=0)


__all__ = [
    "SLUG_MAX_LEN",
    "SLUG_REGEX",
    "AcessoModuloOut",
    "AtribuicaoCreate",
    "AtribuicaoOut",
    "MatrizPermissoesResponse",
    "ModuloCreate",
    "ModuloDoUsuarioOut",
    "ModuloOut",
    "ModuloUpdate",
    "ModulosDoUsuarioResponse",
    "ModulosListResponse",
    "UsuarioMatrizOut",
]
