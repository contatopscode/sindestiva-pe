"""SINDESTIVA-PE · Pydantic schemas — OGMO (notificações + webhooks)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import CanalNotificacaoEnum, StatusNotificacaoEnum


class OgmoNotificacaoBase(BaseModel):
    remanejamento_id: UUID
    canal: CanalNotificacaoEnum
    template_id: str
    assunto: str | None = None
    payload_json: dict
    destinatario_email: str | None = None
    destinatario_webhook_id: UUID | None = None


class OgmoNotificacaoCreate(OgmoNotificacaoBase):
    pass


class OgmoNotificacaoRead(OgmoNotificacaoBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payload_hash_sha256: str
    provider_message_id: str | None
    status: StatusNotificacaoEnum
    tentativas: int
    proxima_tentativa_em: datetime | None
    enviado_at: datetime | None
    entregue_at: datetime | None
    falhou_at: datetime | None
    erro_detalhes: str | None
    pdf_anexo_url: str | None
    created_at: datetime
    updated_at: datetime


class EnviarNotificacaoRequest(BaseModel):
    canal: CanalNotificacaoEnum = CanalNotificacaoEnum.EMAIL
    destinatario_email: str | None = None
    destinatario_webhook_id: UUID | None = None
