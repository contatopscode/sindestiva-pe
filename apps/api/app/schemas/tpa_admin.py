"""SINDESTIVA-PE · Schemas admin — cadastro TPA (DIRIGENTE)."""

from __future__ import annotations

import re
from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import TpaStatusEnum, UserStatusEnum

_CPF_RE = re.compile(r"^\d{11}$")


def _normalize_cpf(value: str) -> str:
    return value.replace(".", "").replace("-", "").strip()


def _validate_matricula_ogmo(value: str) -> str:
    v = value.strip()
    if "," in v:
        raise ValueError("Matrícula OGMO não pode conter vírgula.")
    if len(v) < 1 or len(v) > 10:
        raise ValueError("Matrícula OGMO deve ter entre 1 e 10 caracteres.")
    return v


class AdminTpaFuncaoMeta(BaseModel):
    """Item do catálogo GET /tpas/meta/funcoes (funções ativas)."""

    id: UUID
    codigo: str
    nome: str
    categoria: str


class AdminTpaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    email: str | None
    telefone: str
    user_status: UserStatusEnum
    cpf: str
    nome_completo: str
    matricula_ogmo: str
    funcao_base_id: UUID
    funcao_codigo: str
    funcao_nome: str
    categoria: str
    status_cadastro: TpaStatusEnum
    data_nascimento: date | None = None
    data_admissao: date | None = None
    data_desligamento: date | None = None
    created_at: datetime
    updated_at: datetime


class AdminTpaListResponse(BaseModel):
    items: list[AdminTpaRead]
    total: int


class AdminTpaCreate(BaseModel):
    cpf: str = Field(min_length=11, max_length=14)
    nome_completo: str = Field(min_length=2, max_length=200)
    matricula_ogmo: str = Field(min_length=1, max_length=10)
    telefone: str = Field(min_length=8, max_length=32)
    email: EmailStr | None = None
    funcao_base_id: UUID
    status_cadastro: TpaStatusEnum = TpaStatusEnum.ATIVO
    data_nascimento: date | None = None
    data_admissao: date | None = None

    @field_validator("cpf")
    @classmethod
    def _cpf_digits(cls, value: str) -> str:
        cpf = _normalize_cpf(value)
        if not _CPF_RE.match(cpf):
            raise ValueError("CPF deve conter exatamente 11 dígitos.")
        return cpf

    @field_validator("matricula_ogmo")
    @classmethod
    def _matricula(cls, value: str) -> str:
        return _validate_matricula_ogmo(value)


class AdminTpaUpdate(BaseModel):
    nome_completo: str | None = Field(default=None, min_length=2, max_length=200)
    matricula_ogmo: str | None = Field(default=None, min_length=1, max_length=10)
    telefone: str | None = Field(default=None, min_length=8, max_length=32)
    email: EmailStr | None = None
    funcao_base_id: UUID | None = None
    status_cadastro: TpaStatusEnum | None = None
    data_nascimento: date | None = None
    data_admissao: date | None = None
    data_desligamento: date | None = None

    @field_validator("matricula_ogmo")
    @classmethod
    def _matricula(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_matricula_ogmo(value)

    @model_validator(mode="after")
    def _non_empty_patch(self) -> AdminTpaUpdate:
        if not any(
            getattr(self, f) is not None
            for f in (
                "nome_completo",
                "matricula_ogmo",
                "telefone",
                "email",
                "funcao_base_id",
                "status_cadastro",
                "data_nascimento",
                "data_admissao",
                "data_desligamento",
            )
        ):
            raise ValueError("Informe ao menos um campo para atualizar.")
        return self


__all__ = [
    "AdminTpaCreate",
    "AdminTpaFuncaoMeta",
    "AdminTpaListResponse",
    "AdminTpaRead",
    "AdminTpaUpdate",
]
