"""SINDESTIVA-PE · Pydantic schemas — Remanejamento."""
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


class RemanejamentoCreate(RemanejamentoBase):
    fiscal_id: UUID


class RemanejamentoUpdate(BaseModel):
    status: StatusRemanejamentoEnum | None = None
    observacoes: str | None = None
    nack_motivo: str | None = None


class RemanejamentoRead(RemanejamentoBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codigo_se: str
    snapshot_origem_id: UUID | None
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
    pass


class AprovarRemanejamentoRequest(BaseModel):
    fiscal_id: UUID
    observacoes: str | None = None
