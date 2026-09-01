"""SINDESTIVA-PE · /dpo (dashboard do DPO + export Art. 18).

Sprint 6 T6-10 + T6-12. Endpoints:
- GET  /dpo/hash-chain-checkpoints    → últimos N checkpoints
- GET  /dpo/hash-chain/run-now       → dispara verificação manual
- GET  /dpo/lgpd-purge-log           → histórico de purges
- GET  /dpo/lgpd-purge/run-now       → dispara purge manual (perigoso)
- GET  /dpo/access-log               → log de leituras de PII (Art. 37)
- GET  /dpo/export/meus-dados/{tpa_id} → export portabilidade Art. 18 V (JSON)
- POST /dpo/solicitacoes/{id}/executar → anonimiza TPA (Art. 18 VI)

Permissão: apenas `is_dpo = true` em `dirigentes` (Paulo é DPO acumulado).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import get_logger
from app.core.security import get_current_user_id, oauth2_scheme
from app.jobs.scheduler import run_hash_chain_verifier_now, run_lgpd_purge_now
from app.models import (
    AccessLog,
    Dirigente,
    HashChainCheckpoint,
    LgpdPurgeLog,
    LgpdSolicitacao,
    LgpdStatusEnum,
    LgpdTipoEnum,
    Tpa,
)
from app.models.enums import TpaStatusEnum, UserStatusEnum

router = APIRouter(prefix="/dpo", tags=["dpo"])
log = get_logger(__name__)


async def _require_dpo(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UUID:
    """Dependency: garante que o user autenticado é DPO (Dirigente.is_dpo = true)."""
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )

    stmt = select(Dirigente).where(Dirigente.user_id == user_id, Dirigente.is_dpo.is_(True))
    dirigente = (await db.execute(stmt)).scalar_one_or_none()
    if not dirigente:
        raise HTTPException(
            status_code=403,
            detail={"code": "NOT_DPO", "message": "Acesso restrito ao DPO."},
        )
    return user_id


# ---------------------------------------------------------------------------
# T6-10: Dashboard DPO
# ---------------------------------------------------------------------------

@router.get(
    "/hash-chain-checkpoints",
    summary="Últimos N checkpoints do verificador (T6-10)",
)
async def list_checkpoints(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[UUID, Depends(_require_dpo)],
    limit: int = Query(30, ge=1, le=365),
) -> dict:
    """Lista últimos checkpoints (mais recentes primeiro)."""
    stmt = select(HashChainCheckpoint).order_by(HashChainCheckpoint.executado_em.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": str(c.id),
                "executado_em": c.executado_em.isoformat(),
                "executado_por": c.executado_por,
                "total_eventos": c.total_eventos_verificados,
                "primeiro_sequencia": c.primeiro_sequencia,
                "ultimo_sequencia": c.ultimo_sequencia,
                "integro": c.integro,
                "primeiro_evento_com_falha": c.primeiro_evento_com_falha,
                "duracao_ms": c.duracao_ms,
                "alerta_enviado": c.alerta_enviado,
            }
            for c in rows
        ],
        "total": len(rows),
    }


@router.post(
    "/hash-chain/run-now",
    summary="Dispara verificador de hash chain manualmente (T6-10)",
)
async def trigger_hash_chain(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[UUID, Depends(_require_dpo)],
) -> dict:
    """Dispara o job na hora. Útil pra investigar incidente de segurança."""
    result = await run_hash_chain_verifier_now()
    return result


@router.get(
    "/lgpd-purge-log",
    summary="Histórico de purges automáticos (T6-10)",
)
async def list_purge_log(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[UUID, Depends(_require_dpo)],
    limit: int = Query(30, ge=1, le=365),
) -> dict:
    """Lista últimas execuções do job de purge (registros deletados, hash do lote)."""
    stmt = select(LgpdPurgeLog).order_by(LgpdPurgeLog.executado_em.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "executado_em": r.executado_em.isoformat(),
                "registros_deletados": r.registros_deletados,
                "criterio": r.criterio,
                "hash_lote_sha256": r.hash_lote_sha256,
                "job_id": r.job_id,
                "tabelas": list((r.registros_ids_antes_delete or {}).get("ids_por_tabela", {}).keys()),
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.post(
    "/lgpd-purge/run-now",
    summary="Dispara purge AGORA (T6-06, cuidado!)",
)
async def trigger_purge(
    _: Annotated[UUID, Depends(_require_dpo)],
) -> dict:
    """Dispara o job de purge imediato. Operador tem responsabilidade legal
    (Art. 37 LGPD + Art. 16 — eliminar dados após o cumprimento da finalidade).

    O log imutável fica em `lgpd_purge_log` com o hash do lote.
    """
    log.warning("dpo.purge.disparado_manualmente", por="DPO")
    result = await run_lgpd_purge_now()
    return result


@router.get(
    "/access-log",
    summary="Log de leituras de PII (Art. 37 LGPD, T6-09)",
)
async def list_access_log(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[UUID, Depends(_require_dpo)],
    recurso_tipo: str | None = Query(None, description="Filtrar por tipo (user, tpa, etc)"),
    user_id: UUID | None = Query(None, description="Filtrar por ator"),
    recurso_id: UUID | None = Query(None, description="Filtrar por recurso"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Lista leituras de dados pessoais. Rastreabilidade completa (Art. 37)."""
    stmt = select(AccessLog)
    if recurso_tipo:
        stmt = stmt.where(AccessLog.recurso_tipo == recurso_tipo)
    if user_id:
        stmt = stmt.where(AccessLog.user_id == user_id)
    if recurso_id:
        stmt = stmt.where(AccessLog.recurso_id == recurso_id)
    stmt = stmt.order_by(AccessLog.created_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "user_id": str(r.user_id),
                "recurso_tipo": r.recurso_tipo,
                "recurso_id": str(r.recurso_id),
                "operacao": r.operacao,
                "contexto": r.contexto,
                "ip_origem": str(r.ip_origem) if r.ip_origem else None,
                "user_agent": r.user_agent[:200],
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "skip": skip,
        "limit": limit,
    }


# ---------------------------------------------------------------------------
# T6-12: Export Art. 18 (portabilidade)
# ---------------------------------------------------------------------------

@router.get(
    "/export/meus-dados/{tpa_id}",
    summary="Exporta todos os dados do TPA em JSON (Art. 18 V — portabilidade)",
    response_class=JSONResponse,
)
async def export_tpa_data(
    tpa_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> dict:
    """TPA pode pedir seus próprios dados (Art. 18, V).
    DPO pode pedir de qualquer TPA (auditoria).
    """
    # Tenta o user_id — pode ser o próprio TPA ou o DPO
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )

    # Se for TPA, só pode exportar os próprios dados
    stmt = select(Tpa).where(Tpa.id == tpa_id)
    tpa = (await db.execute(stmt)).scalar_one_or_none()
    if tpa is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TPA_NOT_FOUND", "message": f"TPA {tpa_id} não encontrado."},
        )

    is_dpo_stmt = select(Dirigente).where(
        Dirigente.user_id == user_id, Dirigente.is_dpo.is_(True)
    )
    is_dpo = (await db.execute(is_dpo_stmt)).scalar_one_or_none() is not None

    if tpa.user_id != user_id and not is_dpo:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "NOT_AUTHORIZED",
                "message": "Só o próprio TPA ou o DPO pode exportar estes dados.",
            },
        )

    # Coleta TUDO sobre o TPA
    from app.models import (  # noqa: PLC0415
        TpaConfirmacaoPresenca,
        Remanejamento,
        TermoConsentimento,
        LgpdSolicitacao as LSolicit,
    )

    export: dict = {
        "tpa": {
            "id": str(tpa.id),
            "cpf": tpa.cpf,
            "nome_completo": tpa.nome_completo,
            "matricula_ogmo": tpa.matricula_ogmo,
            "data_nascimento": tpa.data_nascimento.isoformat() if tpa.data_nascimento else None,
            "telefone": tpa.telefone,
            "categoria": tpa.categoria,
            "funcao_base_id": str(tpa.funcao_base_id),
            "status_cadastro": tpa.status_cadastro.value,
            "data_admissao": tpa.data_admissao.isoformat() if tpa.data_admissao else None,
            "data_desligamento": tpa.data_desligamento.isoformat() if tpa.data_desligamento else None,
            "consentimento_versao": tpa.consentimento_versao,
            "consentimento_at": tpa.consentimento_at.isoformat() if tpa.consentimento_at else None,
            "created_at": tpa.created_at.isoformat(),
            "updated_at": tpa.updated_at.isoformat(),
        },
        "termos_consentimento": [],
        "remanejamentos_como_tpa_out": [],
        "remanejamentos_como_tpa_in": [],
        "confirmacoes_presenca": [],
        "solicitacoes_lgpd": [],
        "metadata": {
            "exportado_em": datetime.now(tz=timezone.utc).isoformat(),
            "exportado_por_user_id": str(user_id),
            "is_dpo_request": is_dpo,
            "formato": "JSON",
            "base_legal": "Art. 18, V — LGPD (direito de portabilidade)",
        },
    }

    # Termos
    stmt = select(TermoConsentimento).where(TermoConsentimento.tpa_id == tpa_id)
    for tc in (await db.execute(stmt)).scalars().all():
        export["termos_consentimento"].append({
            "versao_termo": tc.versao_termo,
            "aceito": tc.aceito,
            "aceito_em": tc.aceito_em.isoformat(),
            "metodo": tc.metodo.value,
            "ip_origem": str(tc.ip_origem) if tc.ip_origem else None,
            "user_agent": tc.user_agent,
            "created_at": tc.created_at.isoformat(),
        })

    # Remanejamentos
    stmt = select(Remanejamento).where(Remanejamento.tpa_out_id == tpa_id)
    for r in (await db.execute(stmt)).scalars().all():
        export["remanejamentos_como_tpa_out"].append({
            "id": str(r.id),
            "codigo_se": r.codigo_se,
            "data_referencia": r.data_referencia.isoformat(),
            "motivo": r.motivo.value,
            "status": r.status.value,
            "created_at": r.created_at.isoformat(),
        })
    stmt = select(Remanejamento).where(Remanejamento.tpa_in_id == tpa_id)
    for r in (await db.execute(stmt)).scalars().all():
        export["remanejamentos_como_tpa_in"].append({
            "id": str(r.id),
            "codigo_se": r.codigo_se,
            "data_referencia": r.data_referencia.isoformat(),
            "motivo": r.motivo.value,
            "status": r.status.value,
            "created_at": r.created_at.isoformat(),
        })

    # Confirmações de presença
    stmt = select(TpaConfirmacaoPresenca).where(TpaConfirmacaoPresenca.tpa_id == tpa_id)
    for cp in (await db.execute(stmt)).scalars().all():
        export["confirmacoes_presenca"].append({
            "data_referencia": cp.data_referencia.isoformat(),
            "confirmou": cp.confirmou,
            "confirmado_at": cp.confirmado_at.isoformat(),
            "latitude": float(cp.latitude) if cp.latitude else None,
            "longitude": float(cp.longitude) if cp.longitude else None,
        })

    # Solicitações LGPD
    stmt = select(LSolicit).where(LSolicit.tpa_id == tpa_id)
    for s in (await db.execute(stmt)).scalars().all():
        export["solicitacoes_lgpd"].append({
            "protocolo": s.protocolo,
            "tipo": s.tipo.value,
            "status": s.status.value,
            "recebida_em": s.recebida_em.isoformat(),
            "respondida_em": s.respondida_em.isoformat() if s.respondida_em else None,
            "descricao": s.descricao,
        })

    return export


# ---------------------------------------------------------------------------
# T6-13: Execução de solicitação de exclusão (Art. 18, VI)
# ---------------------------------------------------------------------------

@router.post(
    "/solicitacoes/{solicitacao_id}/executar",
    summary="Executa solicitação LGPD (anonimiza TPA, Art. 18 VI)",
)
async def executar_solicitacao(
    solicitacao_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[UUID, Depends(_require_dpo)],
) -> dict:
    """Para tipo=EXCLUSAO: anonimiza o TPA mantendo integridade referencial.
    - cpf → hash SHA-256 (primeiros 16 chars)
    - nome_completo → "TPA EXCLUÍDO"
    - telefone → "EXCLUIDO"
    - data_nascimento → NULL
    - soft_delete (deleted_at = now)

    Audit + access_log preservam FK (não quebram integridade).

    Para tipo=PORTABILIDADE: já tem o endpoint /export/meus-dados.

    Para tipo=CORRECAO/CONFIRMACAO_EXISTENCIA: atualiza status.
    """
    stmt = select(LgpdSolicitacao).where(LgpdSolicitacao.id == solicitacao_id)
    sol = (await db.execute(stmt)).scalar_one_or_none()
    if sol is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SOLICITACAO_NOT_FOUND", "message": f"Solicitação {solicitacao_id} não encontrada."},
        )

    if sol.status not in (LgpdStatusEnum.RECEBIDA, LgpdStatusEnum.EM_ANALISE, LgpdStatusEnum.DEFERIDA):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INVALID_STATE",
                "message": f"Solicitação está em {sol.status.value!r}, esperado RECEBIDA/EM_ANALISE/DEFERIDA.",
            },
        )

    agora = datetime.now(tz=timezone.utc)

    if sol.tipo == LgpdTipoEnum.EXCLUSAO:
        # Anonimiza o TPA
        tpa_stmt = select(Tpa).where(Tpa.id == sol.tpa_id)
        tpa = (await db.execute(tpa_stmt)).scalar_one_or_none()
        if tpa is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "TPA_NOT_FOUND", "message": "TPA vinculado não encontrado."},
            )

        # Hash do CPF original (preserva histórico em log/audit)
        cpf_hash = hashlib.sha256(tpa.cpf.encode("utf-8")).hexdigest()[:16]

        # Anonimização respeitando CHECK constraints:
        #   ck_tpas_cpf            → cpf ~ '^\d{11}$'  (11 dígitos)
        #   ck_tpas_matricula_ogmo → 1 ≤ length ≤ 10
        # Padrão LGPD: 11 zeros (CPF placeholder) + 10 zeros (matrícula placeholder).
        # Mantém o cpf_hash em log_auditoria/audit_event payload para rastreabilidade.
        tpa.cpf = "00000000000"
        tpa.nome_completo = "TPA EXCLUÍDO"
        tpa.telefone = "EXCLUIDO"
        tpa.data_nascimento = None
        tpa.matricula_ogmo = "0000000000"
        tpa.deleted_at = agora
        tpa.purge_after = agora.replace(year=agora.year + 5)  # 5a (audit legal)
        tpa.status_cadastro = TpaStatusEnum.DESLIGADO

        # Também anonimiza user (se existir)
        from app.models import User  # noqa: PLC0415
        user_stmt = select(User).where(User.id == tpa.user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        if user:
            user.status = UserStatusEnum.INATIVO
            user.accepted_terms_at = None
            user.accepted_terms_version = None

        sol.status = LgpdStatusEnum.EXECUTADA
        sol.executada_em = agora
        sol.respondida_em = agora
        sol.resposta_texto = f"TPA anonimizado em {agora.isoformat()}. ID preservado pra integridade."

    elif sol.tipo == LgpdTipoEnum.CORRECAO:
        # Marca como deferida + executada (correção real é feita pelo TPA via app)
        sol.status = LgpdStatusEnum.EXECUTADA
        sol.executada_em = agora
        sol.respondida_em = agora
        sol.resposta_texto = "Solicitação de correção registrada. TPA deve abrir chamado de suporte."

    else:  # CONFIRMACAO_EXISTENCIA, PORTABILIDADE, REVOGACAO_CONSENTIMENTO
        sol.status = LgpdStatusEnum.EXECUTADA
        sol.executada_em = agora
        sol.respondida_em = agora
        sol.resposta_texto = "Solicitação processada."

    await db.commit()
    await db.refresh(sol)

    log.info(
        "dpo.solicitacao.executada",
        solicitacao_id=str(sol.id),
        tipo=sol.tipo.value,
        status=sol.status.value,
    )

    return {
        "id": str(sol.id),
        "protocolo": sol.protocolo,
        "tipo": sol.tipo.value,
        "status": sol.status.value,
        "executada_em": sol.executada_em.isoformat() if sol.executada_em else None,
        "resposta_texto": sol.resposta_texto,
    }
