"""SINDESTIVA-PE · Pydantic schemas — Scraping (Sprint 2)."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FonteEscalaEnum, StatusScrapingEnum


class ScrapingDispararRequest(BaseModel):
    """Request do `POST /api/scraping/disparar` (admin)."""

    fonte: FonteEscalaEnum = Field(
        default=FonteEscalaEnum.TPA,
        description="Fonte do scrape: TPA (SUAPE) ou ESCALANET (RECIFE).",
    )
    porto: str = Field(
        default="SUAPE",
        pattern=r"^(SUAPE|RECIFE)$",
        description="Slug do porto (SUAPE ou RECIFE).",
    )
    turno: str = Field(
        default="DIURNO",
        pattern=r"^(DIURNO|NOTURNO)$",
        description="Código do turno (DIURNO ou NOTURNO).",
    )
    data: date = Field(
        default_factory=date.today,
        description="Data de referência (default: hoje).",
    )


class ScrapingDispararResponse(BaseModel):
    """Response do `POST /api/scraping/disparar`."""

    sucesso: bool
    escala_origem_id: UUID | None
    fonte: FonteEscalaEnum
    porto: str
    turno: str
    data: date
    status: StatusScrapingEnum
    total_celulas: int
    duracao_ms: int
    layout_mudou: bool
    erro_detalhes: str | None = None


class ScrapingStatusItem(BaseModel):
    """Item do `GET /api/scraping/status`."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fonte: FonteEscalaEnum
    data_referencia: date
    content_hash: str
    status: StatusScrapingEnum
    total_celulas: int
    duracao_ms: int
    scraped_at: datetime
    erro_detalhes: str | None = None


class ScrapingStatusResponse(BaseModel):
    """Response do `GET /api/scraping/status`."""

    total: int
    sucessos: int
    falhas: int
    layout_mudou: int
    itens: list[ScrapingStatusItem]


class LousaAlocacaoItem(BaseModel):
    """Item da resposta de `GET /api/lousa/escalas`."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    faina_id: UUID
    funcao_id: UUID
    data_referencia: date
    trabalhador_matricula: str | None
    fk_mando: int | None
    fk_terno: int | None
    fk_tecnica: int | None
    fk_vigia: int | None


class LousaEscalasResponse(BaseModel):
    """Response do `GET /api/lousa/escalas`."""

    data: date
    porto: str
    turno: str
    total_alocacoes: int
    alocacoes: list[LousaAlocacaoItem]
