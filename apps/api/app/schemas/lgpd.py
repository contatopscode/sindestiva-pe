"""SINDESTIVA-PE · Pydantic schemas — LGPD (termo de consentimento)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LgpdTipoEnum, TermoMetodoEnum


class TermoTextoResponse(BaseModel):
    """Resposta de `GET /lgpd/termo-consentimento/texto`.

    Devolve a versão atual do termo (texto + hash + URL do PDF).
    Cliente frontend exibe num modal de aceite no primeiro login.
    """

    versao: str = Field(description="Versão do termo (semver). Ex: '1.0'")
    texto: str = Field(description="Texto completo do termo (Markdown).")
    texto_hash_sha256: str = Field(description="SHA-256 do texto (pra prova de integridade).")
    pdf_url: str | None = Field(default=None, description="URL do PDF versionado (opcional).")
    obrigatorio: bool = Field(
        default=True, description="Se true, bloquear o app até aceitar."
    )


class TermoAceitarRequest(BaseModel):
    """Body de `POST /lgpd/termo-consentimento/aceitar`."""

    versao: str = Field(min_length=1, max_length=20, description="Versão que está sendo aceita.")
    aceito: bool = Field(description="Se o titular aceita ou recusa explicitamente.")
    metodo: TermoMetodoEnum = Field(
        default=TermoMetodoEnum.PRIMEIRO_LOGIN,
        description="Contexto do aceite (1º login, reconfirmação, etc).",
    )


class TermoAceitarResponse(BaseModel):
    """Resposta de `POST /lgpd/termo-consentimento/aceitar`."""

    id: UUID
    tpa_id: UUID
    versao_termo: str
    aceito: bool
    aceito_em: datetime
    metodo: TermoMetodoEnum
    created_at: datetime


class LgpdSolicitacaoCreate(BaseModel):
    """Body de `POST /lgpd/solicitacoes` (Art. 18 LGPD)."""

    tipo: LgpdTipoEnum
    descricao: str | None = Field(default=None, max_length=2000)


class LgpdSolicitacaoRead(BaseModel):
    """Resposta padrão de solicitação Art. 18."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    protocolo: str
    tpa_id: UUID
    tipo: LgpdTipoEnum
    descricao: str | None
    prazo_resposta: datetime
    recebida_em: datetime
    status: str  # LgpdStatusEnum como str pra evitar import cycle


__all__ = [
    "TermoTextoResponse",
    "TermoAceitarRequest",
    "TermoAceitarResponse",
    "LgpdSolicitacaoCreate",
    "LgpdSolicitacaoRead",
]
