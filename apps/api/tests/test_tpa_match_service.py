"""Testes do matcher matrícula OGMO ↔ TPA + backfill stubs."""
from __future__ import annotations

import secrets
from datetime import date

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.database import session_scope
from app.models import Faina, Funcao, LousaAlocacao, LousaEscalaOrigem, Porto, Tpa, Turno, User
from app.models.enums import FonteEscalaEnum, RoleEnum, StatusScrapingEnum, TpaStatusEnum, UserStatusEnum
from app.services.tpa_match_service import (
    backfill_tpas_from_lousa_alocacao,
    ensure_stub_tpa_for_matricula,
    find_tpa_by_matricula,
    map_tpas_by_matriculas,
    normalize_matricula_ogmo,
)


def test_normalize_matricula_preserva_zeros() -> None:
    assert normalize_matricula_ogmo("  058  ") == "058"
    assert normalize_matricula_ogmo("058") == "058"
    assert normalize_matricula_ogmo("  ") is None
    assert normalize_matricula_ogmo(None) is None


@pytest.mark.asyncio
async def test_find_tpa_hit_e_miss(db_session) -> None:
    funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()
    mat = f"9{secrets.randbelow(10**2):02d}"
    user = User(
        email=f"match-{mat}@test.local",
        role=RoleEnum.TPA,
        status=UserStatusEnum.ATIVO,
        password_hash=None,
    )
    db_session.add(user)
    await db_session.flush()
    tpa = Tpa(
        user_id=user.id,
        cpf=f"{secrets.randbelow(10**9):09d}00",
        nome_completo="Match Test",
        matricula_ogmo=mat,
        telefone="+5581999999999",
        funcao_base_id=funcao.id,
        categoria=funcao.categoria,
        status_cadastro=TpaStatusEnum.ATIVO,
    )
    db_session.add(tpa)
    await db_session.commit()

    hit = await find_tpa_by_matricula(db_session, f"  {mat} ")
    assert hit is not None
    assert hit.id == tpa.id

    miss = await find_tpa_by_matricula(db_session, f"0{mat}")
    if mat.startswith("0"):
        assert miss is not None
    else:
        assert miss is None


@pytest.mark.asyncio
async def test_map_tpas_by_matriculas_batch(db_session) -> None:
    funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()
    mats = [f"M{secrets.token_hex(2)}"[:6] for _ in range(2)]
    for i, mat in enumerate(mats):
        user = User(
            email=f"batch-{mat}@test.local",
            role=RoleEnum.TPA,
            status=UserStatusEnum.ATIVO,
            password_hash=None,
        )
        db_session.add(user)
        await db_session.flush()
        db_session.add(
            Tpa(
                user_id=user.id,
                cpf=f"{secrets.randbelow(10**9):09d}0{i}",
                nome_completo=f"T {mat}",
                matricula_ogmo=mat,
                telefone="+5581999999999",
                funcao_base_id=funcao.id,
                categoria=funcao.categoria,
                status_cadastro=TpaStatusEnum.ATIVO,
            )
        )
    await db_session.commit()

    found = await map_tpas_by_matriculas(db_session, [f" {mats[0]} ", "inexistente"])
    assert mats[0] in found
    assert "inexistente" not in found


@pytest.mark.asyncio
async def test_stub_idempotente(monkeypatch, db_session) -> None:
    monkeypatch.setattr(settings, "allow_tpa_stub", True)
    mat = f"S{secrets.token_hex(2)}"[:5]

    t1 = await ensure_stub_tpa_for_matricula(db_session, mat)
    await db_session.commit()
    assert t1 is not None

    t2 = await ensure_stub_tpa_for_matricula(db_session, mat)
    await db_session.commit()
    assert t2 is not None
    assert t2.id == t1.id

    count = (
        await db_session.execute(
            select(Tpa).where(Tpa.matricula_ogmo == mat)
        )
    ).scalars().all()
    assert len(count) == 1


@pytest.mark.asyncio
async def test_backfill_from_lousa_cria_e_fk(monkeypatch, db_session) -> None:
    monkeypatch.setattr(settings, "allow_tpa_stub", True)
    porto = (await db_session.execute(select(Porto).where(Porto.codigo == "SUAPE"))).scalar_one()
    turno = (await db_session.execute(select(Turno).where(Turno.codigo == "DIURNO"))).scalar_one()
    faina_row = (await db_session.execute(select(Faina).limit(1))).scalar_one()
    funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()
    mat = f"L{secrets.token_hex(2)}"[:6]
    data_ref = date(2099, 1, 15)

    escala = LousaEscalaOrigem(
        fonte=FonteEscalaEnum.TPA,
        porto_id=porto.id,
        turno_id=turno.id,
        data_referencia=data_ref,
        url_origem="http://test",
        content_hash="abc",
        payload_jsonb={},
        duracao_ms=1,
        status=StatusScrapingEnum.SUCESSO,
    )
    db_session.add(escala)
    await db_session.flush()

    db_session.add(
        LousaAlocacao(
            escala_origem_id=escala.id,
            porto_id=porto.id,
            turno_id=turno.id,
            faina_id=faina_row.id,
            funcao_id=funcao.id,
            data_referencia=data_ref,
            trabalhador_matricula=mat,
            trabalhador_id=None,
        )
    )
    await db_session.commit()

    stats = await backfill_tpas_from_lousa_alocacao(db_session, days=30)
    assert stats["criados"] >= 1
    assert stats["fk_atualizados"] >= 1

    aloc = (
        await db_session.execute(
            select(LousaAlocacao).where(LousaAlocacao.escala_origem_id == escala.id)
        )
    ).scalar_one()
    assert aloc.trabalhador_id is not None
    tpa = await find_tpa_by_matricula(db_session, mat)
    assert tpa is not None
    assert aloc.trabalhador_id == tpa.id
