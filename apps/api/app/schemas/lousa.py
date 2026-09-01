"""SINDESTIVA-PE · Pydantic schemas — Lousa (snapshot + cell)."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CellStatusEnum, SnapshotStatusEnum


class LousaCellBase(BaseModel):
    funcao_id: UUID
    faina_id: UUID
    cais: str | None = None
    navio_id: UUID | None = None
    tpa_id: UUID | None = None
    status_celula: CellStatusEnum = CellStatusEnum.NORMAL
    data_referencia: date


class LousaCellRead(LousaCellBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    snapshot_id: UUID
    porto_id: UUID
    turno_id: UUID
    created_at: datetime


class LousaSnapshotBase(BaseModel):
    porto_id: UUID
    turno_id: UUID
    fonte: str = Field(min_length=1, max_length=50)
    url_origem: str | None = None
    html_hash_sha256: str = Field(min_length=64, max_length=64)
    total_celulas: int = Field(ge=0)
    total_tpas_escalados: int = Field(ge=0)
    duracao_scrape_ms: int = Field(ge=0)
    status: SnapshotStatusEnum = SnapshotStatusEnum.OK
    erro_detalhes: str | None = None


class LousaSnapshotRead(LousaSnapshotBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    layout_fingerprint_id: UUID | None
    scraped_at: datetime
    created_at: datetime
    cells: list[LousaCellRead] = []


class LousaAtualResponse(BaseModel):
    """Resposta de `GET /lousa/atual` (snapshot + cells)."""
    snapshot: LousaSnapshotRead
    total_tpas: int
    total_celulas_ocupadas: int
