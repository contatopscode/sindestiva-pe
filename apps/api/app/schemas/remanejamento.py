"""SINDESTIVA-PE · Pydantic schemas — Remanejamento + List."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    MotivoRemanejamentoEnum,
    StatusRemanejamentoEnum,
)


class RemanejamentoBase(BaseModel):
    porto_id: UUID
    turno_id: UUID
    data_referencia: date
    tpa_out_id: UUID
    funcao_origem_id: UUID
    faina_origem_id: UUID
    cais_origem: str | None = None
    tpa_in_id: UUID | None = None
    motivo: MotivoRemanejamentoEnum
    motivo_outro_texto: str | None = None
    base_legal_cct_id: UUID | None = None
    base_legal_texto_livre: str | None = None
    observacoes: str | None = None
    anexo_url: str | None = None
    snapshot_origem_id: UUID | None = None


class RemanejamentoCreate(RemanejamentoBase):
    """Body de `POST /api/v1/remanejamentos`.

    `fiscal_id` é derivado do JWT (não enviado no body).
    """


class RemanejamentoUpdate(BaseModel):
    status: StatusRemanejamentoEnum | None = None
    observacoes: str | None = None
    nack_motivo: str | None = None


class RemanejamentoRead(RemanejamentoBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codigo_se: str
    fiscal_id: UUID
    status: StatusRemanejamentoEnum
    ack_at: datetime | None
    ack_por: str | None
    nack_motivo: str | None
    hash_evento: str
    hash_anterior_id: UUID | None
    created_at: datetime
    updated_at: datetime


class RemanejamentoInDB(RemanejamentoRead):
    """User completo com relacionamentos (uso interno)."""

    pass


class RemanejamentoListResponse(BaseModel):
    """Resposta de `GET /api/v1/remanejamentos` (paginado)."""

    items: list[RemanejamentoRead]
    total: int
    skip: int
    limit: int


class AprovarRemanejamentoRequest(BaseModel):
    """Body de `PATCH /api/v1/remanejamentos/{id}/aprovar`."""

    observacoes: str | None = Field(default=None, max_length=2000)


__all__ = [
    "RemanejamentoBase",
    "RemanejamentoCreate",
    "RemanejamentoUpdate",
    "RemanejamentoRead",
    "RemanejamentoInDB",
    "RemanejamentoListResponse",
    "AprovarRemanejamentoRequest",
]
