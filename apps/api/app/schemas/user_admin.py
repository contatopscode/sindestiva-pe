"""SINDESTIVA-PE · Schemas admin — gestão FISCAL + DIRIGENTE."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.enums import RoleEnum, UserStatusEnum


class AdminUserListResponse(BaseModel):
    items: list[AdminUserRead]
    total: int


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr | None
    telefone: str | None
    role: RoleEnum
    status: UserStatusEnum
    nome_completo: str | None = None
    cpf: str | None = None
    matricula_sindicato: str | None = None
    cargo: str | None = None
    porto_codigo: str | None = None
    turno_codigo: str | None = None
    fiscal_status: str | None = None
    data_inicio: date | None = None
    data_inicio_mandato: date | None = None
    created_at: datetime
    updated_at: datetime


class AdminUserCreate(BaseModel):
    email: EmailStr
    telefone: str = Field(min_length=8, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    role: Literal[RoleEnum.FISCAL, RoleEnum.DIRIGENTE]
    status: UserStatusEnum = UserStatusEnum.ATIVO
    cpf: str = Field(min_length=11, max_length=14)
    nome_completo: str = Field(min_length=2, max_length=200)
    matricula_sindicato: str = Field(min_length=2, max_length=64)
    porto_codigo: str = "SUAPE"
    turno_codigo: str = "DIURNO"
    data_inicio: date | None = None
    cargo: str = "Dirigente"
    data_inicio_mandato: date | None = None

    @model_validator(mode="after")
    def _role_fields(self) -> AdminUserCreate:
        if self.role == RoleEnum.TPA:
            raise ValueError("Role TPA não permitida neste endpoint.")
        return self


class AdminUserUpdate(BaseModel):
    email: EmailStr | None = None
    telefone: str | None = Field(default=None, min_length=8, max_length=32)
    role: Literal[RoleEnum.FISCAL, RoleEnum.DIRIGENTE] | None = None
    status: UserStatusEnum | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=14)
    nome_completo: str | None = Field(default=None, min_length=2, max_length=200)
    matricula_sindicato: str | None = Field(default=None, min_length=2, max_length=64)
    porto_codigo: str | None = None
    turno_codigo: str | None = None
    data_inicio: date | None = None
    cargo: str | None = None
    data_inicio_mandato: date | None = None


__all__ = [
    "AdminUserCreate",
    "AdminUserListResponse",
    "AdminUserRead",
    "AdminUserUpdate",
]
