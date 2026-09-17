"""SINDESTIVA-PE · Schemas GET/PUT /configuracoes."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConfiguracoesRead(BaseModel):
    ogmo_whatsapp: str | None = None
    ogmo_whatsapp_fonte: Literal["db", "env", "none"]
    evolution_configured: bool


class ConfiguracoesUpdate(BaseModel):
    ogmo_whatsapp: str = Field(..., min_length=8, max_length=32)


class NotificacaoPreviewRead(BaseModel):
    canal: str
    texto_whatsapp: str
    assunto_email: str | None = None
    payload_resumo: dict
