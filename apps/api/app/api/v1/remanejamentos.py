"""SINDESTIVA-PE · /remanejamentos (CRUD + aprovar + notificar OGMO)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import get_current_user_id, oauth2_scheme
from app.core.logging import get_logger
from app.models.enums import StatusRemanejamentoEnum
from app.schemas.remanejamento import (
    AprovarRemanejamentoRequest,
    RemanejamentoCreate,
    RemanejamentoListResponse,
    RemanejamentoRead,
)
from app.services.ogmo_notifier import OgmoNotifierError, enviar_email
from app.services.remanejamento_service import RemanejamentoError, aprovar, criar, listar

router = APIRouter(prefix="/remanejamentos", tags=["remanejamentos"])
log = get_logger(__name__)


def _user_id_or_401(token: Annotated[str | None, Depends(oauth2_scheme)]) -> str:
    """Helper: garante user autenticado e retorna o id."""
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )
    return user_id


@router.get("", response_model=RemanejamentoListResponse, summary="Lista remanejamentos (paginado)")
async def list_remanejamentos(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_user_id_or_401)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: StatusRemanejamentoEnum | None = Query(None, description="Filtrar por status"),
) -> RemanejamentoListResponse:
    """Sprint 5: SELECT real com paginação + filtro opcional."""
    items, total = await listar(db, skip=skip, limit=limit, status_filter=status)
    return RemanejamentoListResponse(
        items=[RemanejamentoRead.model_validate(r) for r in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=RemanejamentoRead, status_code=201, summary="Cria remanejamento (T5-01)")
async def create_remanejamento(
    payload: RemanejamentoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str, Depends(_user_id_or_401)],
) -> RemanejamentoRead:
    """Sprint 5: cria remanejamento com hash chain + audit + histórico."""
    # Pegar fiscal_id do user
    from app.models import Fiscal  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    fiscal_stmt = select(Fiscal).where(Fiscal.user_id == user_id)
    fiscal = (await db.execute(fiscal_stmt)).scalar_one_or_none()
    if fiscal is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "NOT_FISCAL",
                "message": "Apenas fiscais podem criar remanejamentos.",
            },
        )

    try:
        rem = await criar(
            db,
            fiscal_id=str(fiscal.id),
            tpa_out_id=str(payload.tpa_out_id),
            tpa_in_id=str(payload.tpa_in_id) if payload.tpa_in_id else None,
            motivo=payload.motivo.value,
            motivo_outro_texto=payload.motivo_outro_texto,
            funcao_origem_id=str(payload.funcao_origem_id),
            faina_origem_id=str(payload.faina_origem_id),
            porto_id=str(payload.porto_id),
            turno_id=str(payload.turno_id),
            data_referencia=payload.data_referencia,
            cais_origem=payload.cais_origem,
            base_legal_cct_id=str(payload.base_legal_cct_id) if payload.base_legal_cct_id else None,
            base_legal_texto_livre=payload.base_legal_texto_livre,
            observacoes=payload.observacoes,
            anexo_url=payload.anexo_url,
            snapshot_origem_id=str(payload.snapshot_origem_id) if payload.snapshot_origem_id else None,
        )
    except RemanejamentoError as e:
        raise HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})

    return RemanejamentoRead.model_validate(rem)


@router.patch("/{remanejamento_id}/aprovar", response_model=RemanejamentoRead, summary="Aprova remanejamento (T5-10)")
async def aprovar_remanejamento(
    remanejamento_id: UUID,
    payload: AprovarRemanejamentoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str, Depends(_user_id_or_401)],
) -> RemanejamentoRead:
    """Sprint 5: status PENDENTE → APROVADO."""
    from app.models import Fiscal  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    fiscal_stmt = select(Fiscal).where(Fiscal.user_id == user_id)
    fiscal = (await db.execute(fiscal_stmt)).scalar_one_or_none()
    if fiscal is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "NOT_FISCAL", "message": "Apenas fiscais podem aprovar."},
        )

    try:
        rem = await aprovar(
            db,
            remanejamento_id=str(remanejamento_id),
            fiscal_id=str(fiscal.id),
            observacoes=payload.observacoes,
        )
    except RemanejamentoError as e:
        raise HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})

    return RemanejamentoRead.model_validate(rem)


@router.post(
    "/{remanejamento_id}/notificar-ogmo",
    response_model=dict,
    summary="Envia notificação ao OGMO (T5-04, SLA 5min)",
)
async def notificar_ogmo(
    remanejamento_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_user_id_or_401)],
) -> dict:
    """Sprint 5: dispara envio de e-mail ao OGMO com PDF + hash.

    Funciona mesmo sem resposta do OGMO (R1 do plano).
    """
    try:
        notif = await enviar_email(db, remanejamento_id=str(remanejamento_id))
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
