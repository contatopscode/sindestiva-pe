"""SINDESTIVA-PE · Pydantic schemas — User."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import RoleEnum, UserStatusEnum


class UserBase(BaseModel):
    email: EmailStr | None = None
    telefone: str | None = None
    role: RoleEnum
    status: UserStatusEnum = UserStatusEnum.PENDENTE_ACEITE


class UserCreate(UserBase):
    password: str | None = Field(default=None, min_length=8, max_length=128)
    accepted_terms_version: str | None = None


class UserUpdate(BaseModel):
    telefone: str | None = None
    status: UserStatusEnum | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    failed_login_count: int
    last_login_at: datetime | None
    accepted_terms_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserInDB(UserRead):
    """User completo com relacionamentos (uso interno)."""
    pass


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
