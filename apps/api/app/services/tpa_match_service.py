"""SINDESTIVA-PE · Matcher matrícula OGMO ↔ cadastro TPA (T2-05).

Regra: trim em whitespace; comparação exata com `tpas.matricula_ogmo`
(sem remover zeros à esquerda).
"""
from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models import Funcao, Tpa, User
from app.models.enums import RoleEnum, TpaStatusEnum, UserStatusEnum

log = get_logger(__name__)

DEFAULT_STUB_FUNCAO_CODIGO = "TECNICA_01"
DEFAULT_STUB_CATEGORIA = "TECNICA"


def normalize_matricula_ogmo(raw: str | None) -> str | None:
    """Normaliza matrícula para lookup (strip; vazio → None)."""
    if raw is None:
        return None
    mat = raw.strip()
    return mat if mat else None


def synthetic_cpf_for_matricula(matricula_ogmo: str) -> str:
    """CPF sintético 11 dígitos, determinístico por matrícula (só stubs)."""
    digest = sha256(matricula_ogmo.encode("utf-8")).hexdigest()
    n = int(digest[:16], 16) % 10**11
    return f"{n:011d}"


def stub_email_for_matricula(matricula_ogmo: str) -> str:
    safe = matricula_ogmo.replace("@", "_").replace(" ", "_")[:40]
    return f"tpa-stub-{safe}@stub.lousa.local"


async def find_tpa_by_matricula(
    db: AsyncSession,
    matricula_raw: str | None,
) -> Tpa | None:
    """Resolve um TPA por matrícula OGMO (trim + match exato)."""
    mat = normalize_matricula_ogmo(matricula_raw)
    if mat is None:
        return None
    stmt = select(Tpa).where(Tpa.matricula_ogmo == mat)
    return (await db.execute(stmt)).scalar_one_or_none()


async def map_tpas_by_matriculas(
    db: AsyncSession,
    matriculas_raw: Iterable[str | None],
) -> dict[str, Tpa]:
    """Batch lookup: matrícula normalizada → Tpa."""
    matriculas = {
        m
        for raw in matriculas_raw
        if (m := normalize_matricula_ogmo(raw)) is not None
    }
    if not matriculas:
        return {}
    rows = (
        await db.execute(select(Tpa).where(Tpa.matricula_ogmo.in_(matriculas)))
    ).scalars().all()
    return {t.matricula_ogmo: t for t in rows}


async def ensure_stub_tpa_for_matricula(
    db: AsyncSession,
    matricula_raw: str,
    *,
    allow_stub: bool | None = None,
) -> Tpa | None:
    """Cria User+Tpa stub se não existir e stubs estão permitidos."""
    mat = normalize_matricula_ogmo(matricula_raw)
    if mat is None:
        return None

    existing = await find_tpa_by_matricula(db, mat)
    if existing is not None:
        return existing

    if allow_stub is None:
        allow_stub = settings.allow_tpa_stub
    if not allow_stub:
        return None

    funcao = (
        await db.execute(
            select(Funcao).where(Funcao.codigo == DEFAULT_STUB_FUNCAO_CODIGO)
        )
    ).scalar_one_or_none()
    if funcao is None:
        funcao = (await db.execute(select(Funcao).limit(1))).scalar_one_or_none()
    if funcao is None:
        log.warning("tpa_match.stub_sem_funcao", matricula=mat)
        return None

    email = stub_email_for_matricula(mat)
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            telefone=None,
            password_hash=None,
            role=RoleEnum.TPA,
            status=UserStatusEnum.ATIVO,
        )
        db.add(user)
        await db.flush()
    else:
        user.role = RoleEnum.TPA
        user.password_hash = None

    tpa = (await db.execute(select(Tpa).where(Tpa.user_id == user.id))).scalar_one_or_none()
    cpf = synthetic_cpf_for_matricula(mat)
    if tpa is None:
        tpa = Tpa(
            user_id=user.id,
            cpf=cpf,
            nome_completo=f"TPA Stub {mat}",
            matricula_ogmo=mat,
            telefone="+5581900000000",
            funcao_base_id=funcao.id,
            categoria=funcao.categoria or DEFAULT_STUB_CATEGORIA,
            status_cadastro=TpaStatusEnum.ATIVO,
            data_admissao=None,
            consentimento_at=None,
            consentimento_versao=None,
        )
        db.add(tpa)
        await db.flush()
        log.info("tpa_match.stub_criado", matricula=mat, tpa_id=str(tpa.id))
    else:
        tpa.matricula_ogmo = mat

    return tpa


async def backfill_tpas_from_lousa_alocacao(
    db: AsyncSession,
    *,
    days: int = 14,
    allow_stub: bool | None = None,
) -> dict[str, int]:
    """Cria stubs para matrículas DISTINCT em `lousa_alocacao` recentes."""
    from datetime import date, timedelta

    from sqlalchemy import distinct

    from app.models import LousaAlocacao

    if allow_stub is None:
        allow_stub = settings.allow_tpa_stub
    if not allow_stub:
        return {"skipped": 1, "criados": 0, "ja_existiam": 0, "allow_tpa_stub": 0}

    cutoff = date.today() - timedelta(days=max(days, 1))
    stmt = (
        select(distinct(LousaAlocacao.trabalhador_matricula))
        .where(
            LousaAlocacao.trabalhador_matricula.is_not(None),
            LousaAlocacao.data_referencia >= cutoff,
        )
    )
    matriculas = [
        normalize_matricula_ogmo(row[0])
        for row in (await db.execute(stmt)).all()
        if normalize_matricula_ogmo(row[0]) is not None
    ]

    criados = 0
    ja_existiam = 0
    for mat in matriculas:
        antes = await find_tpa_by_matricula(db, mat)
        if antes is not None:
            ja_existiam += 1
            continue
        novo = await ensure_stub_tpa_for_matricula(
            db, mat, allow_stub=True,
        )
        if novo is not None:
            criados += 1

    # Backfill trabalhador_id nas alocações recentes sem FK.
    tpa_map = await map_tpas_by_matriculas(db, matriculas)
    aloc_stmt = select(LousaAlocacao).where(
        LousaAlocacao.data_referencia >= cutoff,
        LousaAlocacao.trabalhador_id.is_(None),
        LousaAlocacao.trabalhador_matricula.is_not(None),
    )
    alocacoes = (await db.execute(aloc_stmt)).scalars().all()
    fk_atualizados = 0
    for aloc in alocacoes:
        mat = normalize_matricula_ogmo(aloc.trabalhador_matricula)
        if mat is None:
            continue
        tpa = tpa_map.get(mat)
        if tpa is None:
            tpa = await find_tpa_by_matricula(db, mat)
        if tpa is None:
            continue
        aloc.trabalhador_id = tpa.id
        aloc.trabalhador_matricula = mat
        fk_atualizados += 1
        tpa_map[mat] = tpa

    await db.commit()
    return {
        "matriculas_distintas": len(matriculas),
        "criados": criados,
        "ja_existiam": ja_existiam,
        "fk_atualizados": fk_atualizados,
        "allow_tpa_stub": 1,
    }


__all__ = [
    "backfill_tpas_from_lousa_alocacao",
    "ensure_stub_tpa_for_matricula",
    "find_tpa_by_matricula",
    "map_tpas_by_matriculas",
    "normalize_matricula_ogmo",
    "synthetic_cpf_for_matricula",
]
