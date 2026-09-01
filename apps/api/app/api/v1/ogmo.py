"""SINDESTIVA-PE · /ogmo (envio de notificação + status).

Sprint 5 T5-04: implementação real do envio de e-mail ao OGMO com PDF.
A rota POST /notificacoes/{remanejamento_id}/enviar é mantida como
ALIAS do endpoint canônico em /remanejamentos/{id}/notificar-ogmo.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import get_current_user_id, oauth2_scheme
from app.core.logging import get_logger
from app.models import OgmoNotificacao
from app.schemas.ogmo import EnviarNotificacaoRequest
from app.services.ogmo_notifier import OgmoNotifierError, enviar_email

router = APIRouter(prefix="/ogmo", tags=["ogmo"])
log = get_logger(__name__)


@router.post(
    "/notificacoes/{remanejamento_id}/enviar",
    summary="(alias) Envia notificação ao OGMO (use /remanejamentos/{id}/notificar-ogmo)",
)
async def enviar_notificacao(
    remanejamento_id: str,
    payload: EnviarNotificacaoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> dict:
    """Alias mantido pra retrocompatibilidade. Endpoint canônico é
    `POST /api/v1/remanejamentos/{remanejamento_id}/notificar-ogmo`."""
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )

    try:
        notif = await enviar_email(
            db,
            remanejamento_id=remanejamento_id,
            canal=payload.canal,
        )
    except OgmoNotifierError as e:
        raise HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})

    return {
        "id": str(notif.id),
        "remanejamento_id": str(notif.remanejamento_id),
        "status": notif.status.value,
        "canal": notif.canal.value,
        "destinatario": notif.destinatario_email,
        "payload_hash_sha256": notif.payload_hash_sha256,
        "enviado_at": notif.enviado_at.isoformat() if notif.enviado_at else None,
        "provider_message_id": notif.provider_message_id,
        "erro_detalhes": notif.erro_detalhes,
        "pdf_anexo_url": notif.pdf_anexo_url,
    }


@router.get(
    "/notificacoes/{notificacao_id}/status",
    summary="Status de uma notificação (T5-09)",
)
async def get_status(
    notificacao_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> dict:
    """Sprint 5: SELECT em ogmo_notificacoes."""
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )

    stmt = select(OgmoNotificacao).where(OgmoNotificacao.id == notificacao_id)
    notif = (await db.execute(stmt)).scalar_one_or_none()
    if notif is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOTIFICACAO_NOT_FOUND", "message": f"Notificação {notificacao_id} não encontrada."},
        )

    return {
        "id": str(notif.id),
        "remanejamento_id": str(notif.remanejamento_id),
        "status": notif.status.value,
        "canal": notif.canal.value,
        "tentativas": notif.tentativas,
        "proxima_tentativa_em": notif.proxima_tentativa_em.isoformat() if notif.proxima_tentativa_em else None,
        "enviado_at": notif.enviado_at.isoformat() if notif.enviado_at else None,
        "entregue_at": notif.entregue_at.isoformat() if notif.entregue_at else None,
        "falhou_at": notif.falhou_at.isoformat() if notif.falhou_at else None,
        "erro_detalhes": notif.erro_detalhes,
        "ack_por": notif.provider_message_id,
    }
