"""SINDESTIVA-PE · /ogmo (envio de notificação + status)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.core.logging import get_logger
from app.schemas.ogmo import EnviarNotificacaoRequest
from app.services.ogmo_notifier import OgmoNotifier

router = APIRouter(prefix="/ogmo", tags=["ogmo"])
log = get_logger(__name__)


@router.post(
    "/notificacoes/{remanejamento_id}/enviar",
    summary="Envia notificação ao OGMO (M5)",
)
async def enviar_notificacao(
    remanejamento_id: str,
    payload: EnviarNotificacaoRequest,
    db: AsyncSession = Depends(get_db),
    _caller: str = Depends(require_user),
) -> dict:
    """Sprint 0: stub. Sprint 5 T5-04: SLA de 5min entre criação e envio."""
    notifier = OgmoNotifier(db)
    log.info(
        "ogmo.enviar.stub",
        remanejamento_id=remanejamento_id,
        canal=payload.canal,
    )
    return await notifier.enviar_email(remanejamento_id, payload.model_dump())


@router.get(
    "/notificacoes/{notificacao_id}/status",
    summary="Status de uma notificação",
)
async def get_status(
    notificacao_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: ARG001
    _caller: str = Depends(require_user),
) -> dict:
    """Sprint 0: stub. Sprint 5: SELECT em ogmo_notificacoes."""
    return {
        "id": notificacao_id,
        "status": "PENDENTE",
        "tentativas": 0,
        "stub": True,
    }
