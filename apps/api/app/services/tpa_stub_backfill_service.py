"""SINDESTIVA-PE · Stubs de TPA a partir de matrículas raspadas na lousa.

Cria User(role=TPA) + Tpa para matrículas DISTINCT em `lousa_alocacao`
quando `ALLOW_TPA_STUB=1`. Idempotente por `matricula_ogmo`.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models import Funcao, LousaAlocacao, Tpa, User
from app.models.enums import RoleEnum, TpaStatusEnum, UserStatusEnum
from app.services.tpa_match_service import (
    expand_matriculas_from_valores,
    is_valid_matricula_ogmo_storage,
    load_tpas_by_matriculas,
    normalize_matricula_ogmo,
    split_matriculas_celula,
)

log = get_logger(__name__)

DEFAULT_FUNCAO_CODIGO = "TECNICA_01"
DEFAULT_CATEGORIA = "TECNICA"


def synthetic_cpf_for_matricula(matricula: str) -> str:
    """CPF sintético determinístico (11 dígitos) — não é documento real."""
    digest = hashlib.sha256(f"sindestiva-stub:{matricula}".encode()).hexdigest()
    nine = str(int(digest[:16], 16) % 10**9).zfill(9)
    return f"{nine}00"


def _stub_email(matricula: str) -> str:
    safe = matricula.replace("@", "_")[:10]
    return f"tpa-stub-{safe}@stub.lousa.local"


async def _default_funcao(db: AsyncSession) -> Funcao:
    funcao = (
        await db.execute(select(Funcao).where(Funcao.codigo == DEFAULT_FUNCAO_CODIGO))
    ).scalar_one_or_none()
    if funcao is None:
        funcao = (await db.execute(select(Funcao).limit(1))).scalar_one()
    return funcao


async def distinct_matriculas_recentes(
    db: AsyncSession,
    *,
    days: int = 30,
) -> tuple[list[str], int]:
    """Matrículas individuais (split vírgula) válidas para `tpas.matricula_ogmo`."""
    since = date.today() - timedelta(days=days)
    stmt = (
        select(distinct(LousaAlocacao.trabalhador_matricula))
        .where(
            LousaAlocacao.trabalhador_matricula.is_not(None),
            LousaAlocacao.data_referencia >= since,
        )
    )
    raw = (await db.execute(stmt)).scalars().all()
    skipped_invalid = 0
    for cell_value in raw:
        for token in split_matriculas_celula(cell_value):
            if not is_valid_matricula_ogmo_storage(token):
                skipped_invalid += 1
                log.warning(
                    "tpa_stub_backfill.skip_matricula_invalida",
                    token=token,
                    celula=cell_value,
                )
    matriculas = expand_matriculas_from_valores(raw)
    return matriculas, skipped_invalid


async def ensure_stub_tpa_for_matricula(
    db: AsyncSession,
    matricula: str,
    *,
    funcao: Funcao | None = None,
) -> tuple[Tpa, bool]:
    """Garante Tpa para matrícula. Retorna (tpa, created)."""
    key = normalize_matricula_ogmo(matricula)
    if not key:
        raise ValueError("matricula vazia")
    if not is_valid_matricula_ogmo_storage(key):
        raise ValueError(f"matricula invalida para tpas: {key!r}")

    existing = await load_tpas_by_matriculas(db, [key])
    if key in existing:
        return existing[key], False

    if not settings.allow_tpa_stub:
        raise PermissionError("ALLOW_TPA_STUB desabilitado")

    if funcao is None:
        funcao = await _default_funcao(db)

    email = _stub_email(key)
    telefone = "+5581900000000"
    cpf = synthetic_cpf_for_matricula(key)

    stmt_u = select(User).where(User.email == email)
    user = (await db.execute(stmt_u)).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            telefone=telefone,
            password_hash=None,
            role=RoleEnum.TPA,
            status=UserStatusEnum.ATIVO,
        )
        db.add(user)
        await db.flush()
    else:
        user.role = RoleEnum.TPA
        user.telefone = telefone

    tpa = Tpa(
        user_id=user.id,
        cpf=cpf,
        nome_completo=f"TPA Stub {key}",
        matricula_ogmo=key,
        telefone=telefone,
        funcao_base_id=funcao.id,
        categoria=DEFAULT_CATEGORIA,
        status_cadastro=TpaStatusEnum.ATIVO,
        data_admissao=date.today(),
        consentimento_at=None,
        consentimento_versao=None,
    )
    db.add(tpa)
    await db.flush()
    log.info("tpa_stub_backfill.criado", matricula=key, tpa_id=str(tpa.id))
    return tpa, True


async def _link_trabalhador_ids(
    db: AsyncSession,
    *,
    days: int,
    tpa_map: dict[str, Tpa],
) -> int:
    """Preenche `trabalhador_id` (1 FK por célula — multi-TPA usa 1º token resolvido)."""
    since = date.today() - timedelta(days=days)
    stmt = select(LousaAlocacao).where(
        LousaAlocacao.trabalhador_id.is_(None),
        LousaAlocacao.trabalhador_matricula.is_not(None),
        LousaAlocacao.data_referencia >= since,
    )
    alocs = (await db.execute(stmt)).scalars().all()
    linked = 0
    for aloc in alocs:
        tokens = [
            t
            for t in split_matriculas_celula(aloc.trabalhador_matricula)
            if is_valid_matricula_ogmo_storage(t)
        ]
        if not tokens:
            continue
        tpa = None
        for token in tokens:
            tpa = tpa_map.get(token)
            if tpa is not None:
                break
        if tpa is None:
            continue
        aloc.trabalhador_id = tpa.id
        linked += 1
    return linked


async def backfill_stubs_from_lousa_alocacao(
    db: AsyncSession,
    *,
    days: int = 30,
    link_alocacoes: bool = True,
) -> dict[str, int | bool | str]:
    """Cria stubs faltantes e opcionalmente preenche `trabalhador_id`."""
    if not settings.allow_tpa_stub:
        return {
            "ok": True,
            "skipped": True,
            "reason": "ALLOW_TPA_STUB=0",
            "created": 0,
            "existing": 0,
            "linked_alocacoes": 0,
        }

    matriculas, skipped_invalid = await distinct_matriculas_recentes(db, days=days)
    funcao = await _default_funcao(db)
    created = 0
    existing = 0
    for mat in matriculas:
        _, was_created = await ensure_stub_tpa_for_matricula(db, mat, funcao=funcao)
        if was_created:
            created += 1
        else:
            existing += 1

    linked = 0
    if link_alocacoes and matriculas:
        tpa_map = await load_tpas_by_matriculas(db, matriculas)
        linked = await _link_trabalhador_ids(db, days=days, tpa_map=tpa_map)

    await db.commit()
    return {
        "ok": True,
        "skipped": False,
        "matriculas_seen": len(matriculas),
        "skipped_invalid_tokens": skipped_invalid,
        "created": created,
        "existing": existing,
        "linked_alocacoes": linked,
    }


__all__ = [
    "backfill_stubs_from_lousa_alocacao",
    "distinct_matriculas_recentes",
    "ensure_stub_tpa_for_matricula",
    "synthetic_cpf_for_matricula",
]
