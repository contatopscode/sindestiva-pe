"""SINDESTIVA-PE · Pydantic schemas — Navio (catálogo, DD v1 §3.10).

Contrato de `POST /api/v1/navios`. A validação aqui é a primeira
barreira do bug "erro ao salvar navio": normaliza o que o formulário
manda (strings vazias, IMO em formatos diferentes) ANTES de bater no
índice único `uq_navios_imo`.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

# Tipos de operação aceitos no catálogo (DD v1 §3.10). Não virou Enum no
# banco (coluna é Text livre) — validamos na borda pra não poluir o BI
# com variações de grafia.
TIPOS_OPERACAO = (
    "CONTAINER",
    "RO_RO",
    "GRANEL_SOLIDO",
    "GRANEL_LIQUIDO",
    "CARGA_GERAL",
    "PASSAGEIROS",
    "OUTRO",
)

_IMO_RE = re.compile(r"^(?:IMO)?\s*(\d{7})$", re.IGNORECASE)

NomeNavio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class NavioBase(BaseModel):
    """Campos editáveis de um navio."""

    # `extra="ignore"` (default do Pydantic v2): um front desatualizado
    # mandando campo a mais não deve resultar em 422.
    model_config = ConfigDict(str_strip_whitespace=True)

    nome: NomeNavio
    imo: str | None = None
    bandeira: str | None = None
    tipo_operacao: str | None = None

    @field_validator("imo", mode="before")
    @classmethod
    def _normalizar_imo(cls, v: object) -> str | None:
        """`9319466` / `imo 9319466` / `IMO9319466` → `IMO9319466`.

        String vazia vira `None`: se virasse `''`, o índice único
        `uq_navios_imo` trataria como valor real e o segundo navio
        cadastrado sem IMO estouraria 409 sem motivo.
        """
        if v is None:
            return None
        texto = str(v).strip()
        if not texto:
            return None
        match = _IMO_RE.match(texto)
        if match is None:
            msg = "IMO deve ter 7 dígitos (ex.: IMO9319466 ou 9319466)."
            raise ValueError(msg)
        return f"IMO{match.group(1)}"

    @field_validator("bandeira", mode="before")
    @classmethod
    def _normalizar_bandeira(cls, v: object) -> str | None:
        if v is None:
            return None
        texto = str(v).strip()
        if not texto:
            return None
        if len(texto) > 60:
            msg = "Bandeira deve ter no máximo 60 caracteres."
            raise ValueError(msg)
        return texto

    @field_validator("tipo_operacao", mode="before")
    @classmethod
    def _normalizar_tipo(cls, v: object) -> str | None:
        if v is None:
            return None
        texto = str(v).strip().upper().replace("-", "_").replace(" ", "_")
        if not texto:
            return None
        if texto not in TIPOS_OPERACAO:
            opcoes = ", ".join(TIPOS_OPERACAO)
            msg = f"Tipo de operação inválido. Valores aceitos: {opcoes}."
            raise ValueError(msg)
        return texto


class NavioCreate(NavioBase):
    """Body de `POST /api/v1/navios`."""


class NavioRead(NavioBase):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: UUID
    created_at: datetime


class NavioListResponse(BaseModel):
    """Resposta de `GET /api/v1/navios` (paginado)."""

    items: list[NavioRead]
    total: int
    skip: int
    limit: int
