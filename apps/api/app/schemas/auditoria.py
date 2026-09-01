"""SINDESTIVA-PE · Pydantic schemas — Auditoria (audit_events, access_log)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequencia: int
    entity_type: str
    entity_id: UUID | None
    event_type: str
    actor_user_id: UUID | None
    actor_role: str | None
    actor_ip: str | None
    payload_after: dict[str, Any]
    hash_anterior: str | None
    hash_evento: str
    criado_em: datetime


class VerificarHashChainResponse(BaseModel):
    integro: bool
    total_eventos: int
    primeiro_evento_com_falha: int | None = None
    duracao_ms: int = Field(ge=0)
    executado_em: datetime
