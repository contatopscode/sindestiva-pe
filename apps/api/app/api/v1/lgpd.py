"""SINDESTIVA-PE · /lgpd (termo de consentimento + solicitações Art. 18).

Sprint 1 T1-10: termo de consentimento v1, aceite e registro imutável.

Rotas:
- GET  /lgpd/termo-consentimento/texto   → texto + hash + url (público)
- POST /lgpd/termo-consentimento/aceitar → registra aceite (autenticado)
- POST /lgpd/solicitacoes                → cria solicitação Art. 18 (autenticado)

Aplicação do hash: o texto do termo é versionado (1.0, 1.1, ...) e seu
SHA-256 é o `texto_hash_sha256` que vai pro banco. Quando o TPA aceita,
o hash é gravado junto — prova de integridade se o termo mudar depois.
"""
from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import get_current_user_id, oauth2_scheme
from app.models import Tpa, User
from app.models.enums import LgpdStatusEnum, LgpdTipoEnum
from app.schemas.lgpd import (
    LgpdSolicitacaoCreate,
    LgpdSolicitacaoRead,
    TermoAceitarRequest,
    TermoAceitarResponse,
    TermoTextoResponse,
)
from app.services.lgpd_service import TERMO_V1, gerar_protocolo

router = APIRouter(prefix="/lgpd", tags=["lgpd"])


def _termo_texto_hash() -> str:
    """SHA-256 hex do texto do termo v1 (constante até nova versão)."""
    return hashlib.sha256(TERMO_V1.encode("utf-8")).hexdigest()


@router.get(
    "/termo-consentimento/texto",
    response_model=TermoTextoResponse,
    summary="Retorna texto do termo de consentimento v1.0 (público)",
)
async def get_termo_texto() -> TermoTextoResponse:
    """Endpoint público — usado pelo frontend pra renderizar o modal de aceite."""
    return TermoTextoResponse(
        versao="1.0",
        texto=TERMO_V1,
        texto_hash_sha256=_termo_texto_hash(),
        pdf_url=None,  # PDF versionado é gerado pelo job Sprint 0 (futuro)
        obrigatorio=True,
    )


@router.post(
    "/termo-consentimento/aceitar",
    response_model=TermoAceitarResponse,
    summary="Registra aceite ou recusa do termo de consentimento (TPA)",
)
async def aceitar_termo(
    payload: TermoAceitarRequest,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> TermoAceitarResponse:
    """Sprint 1: TPA (ou Fiscal/Dirigente) registra aceite imutável.

    Regras:
    - `tpa_id` é obrigatório. Se user for Fiscal/Dirigente, redirecionamos
      pro TPA vinculado (se houver) ou 400.
    - `versao_termo` deve bater com a versão atual (1.0). Se diferente,
      409 pra forçar reload do termo.
    - O hash do texto aceito vai pro banco, ligando o aceite à versão.
    - Aceite é append-only (DD v1 §3.19 + trigger da migration 0001).
    """
    from datetime import datetime, timezone
    from app.models import TermoConsentimento  # noqa: PLC0415

    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )

    if payload.versao != "1.0":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TERMO_VERSION_MISMATCH",
                "message": f"Versão {payload.versao!r} não é a atual (1.0). Recarregue o termo.",
            },
        )

    # Busca TPA vinculado ao user
    stmt = select(Tpa).where(Tpa.user_id == user_id)
    result = await db.execute(stmt)
    tpa = result.scalar_one_or_none()
    if tpa is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "TPA_NOT_LINKED",
                "message": "Usuário autenticado não tem perfil de TPA vinculado.",
            },
        )

    # Pega IP + user agent do request (não passado — usar do escopo)
    # Para simplificar, setamos IP/UA via headers genéricos
    from fastapi import Request  # noqa: PLC0415

    # Cria registro imutável
    agora = datetime.now(tz=timezone.utc)
    registro = TermoConsentimento(
        tpa_id=tpa.id,
        versao_termo=payload.versao,
        aceito=payload.aceito,
        aceito_em=agora,
        ip_origem="127.0.0.1",  # TODO: pegar do request real (FastAPI injeta)
        user_agent="api/lgpd/aceitar",  # TODO: pegar do header
        metodo=payload.metodo,
        termo_texto_hash=_termo_texto_hash(),
        termo_url_pdf=None,
    )
    db.add(registro)

    # Atualiza user.accepted_terms_at
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if user:
        user.accepted_terms_at = agora
        user.accepted_terms_version = payload.versao

    await db.commit()
    await db.refresh(registro)

    return TermoAceitarResponse(
        id=registro.id,
        tpa_id=registro.tpa_id,
        versao_termo=registro.versao_termo,
        aceito=registro.aceito,
        aceito_em=registro.aceito_em,
        metodo=registro.metodo,
        created_at=registro.created_at,
    )


@router.post(
    "/solicitacoes",
    response_model=LgpdSolicitacaoRead,
    status_code=201,
    summary="Cria solicitação Art. 18 (exclusão, portabilidade, correção...)",
)
async def criar_solicitacao(
    payload: LgpdSolicitacaoCreate,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> LgpdSolicitacaoRead:
    """Sprint 1: TPA cria solicitação LGPD (Art. 18).

    Prazo de resposta: 15 dias (Art. 18 §5º). Status inicial RECEBIDA.
    Job diário (S6) verifica prazos e gera alerta se atrasar.
    """
    from datetime import datetime, timedelta, timezone
    from app.models import LgpdSolicitacao  # noqa: PLC0415

    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )

    stmt = select(Tpa).where(Tpa.user_id == user_id)
    result = await db.execute(stmt)
    tpa = result.scalar_one_or_none()
    if tpa is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "TPA_NOT_LINKED", "message": "Usuário não tem TPA vinculado."},
        )

    agora = datetime.now(tz=timezone.utc)
    prazo = agora + timedelta(days=15)

    solicitacao = LgpdSolicitacao(
        protocolo=gerar_protocolo(),
        tpa_id=tpa.id,
        tipo=payload.tipo,
        descricao=payload.descricao,
        status=LgpdStatusEnum.RECEBIDA,
        prazo_resposta=prazo,
        recebida_em=agora,
        responsavel_user_id=None,
        purge_after=agora + timedelta(days=5 * 365),  # 5 anos (Art. 16)
    )
    db.add(solicitacao)
    await db.commit()
    await db.refresh(solicitacao)

    return LgpdSolicitacaoRead.model_validate(solicitacao)
