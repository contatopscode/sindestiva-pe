"""SINDESTIVA-PE · Testes do matcher matrícula OGMO ↔ TPA."""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy import select

from app.models import Tpa
from app.services.tpa_match_service import (
    expand_matriculas_from_valores,
    is_valid_matricula_ogmo_storage,
    load_tpas_by_matriculas,
    normalize_matricula_ogmo,
    resolve_tpa_by_matricula,
    split_matriculas_celula,
)


def test_normalize_matricula_trim_sem_strip_zeros() -> None:
    assert normalize_matricula_ogmo("  058  ") == "058"
    assert normalize_matricula_ogmo("012") == "012"
    assert normalize_matricula_ogmo("012") != "12"
    assert normalize_matricula_ogmo("") is None
    assert normalize_matricula_ogmo(None) is None


def test_split_matriculas_celula_escalanet_multi() -> None:
    assert split_matriculas_celula("100193,101426") == ["100193", "101426"]
    assert split_matriculas_celula(" 100193 , 101426 ") == ["100193", "101426"]
    assert expand_matriculas_from_valores(["100193,101426"]) == [
        "100193",
        "101426",
    ]


def test_is_valid_matricula_ogmo_storage_length_check() -> None:
    assert is_valid_matricula_ogmo_storage("162") is True
    assert is_valid_matricula_ogmo_storage("100193,101426") is False
    assert is_valid_matricula_ogmo_storage("12345678901") is False


@pytest.mark.asyncio
async def test_resolve_tpa_hit_e_miss(db_session) -> None:
    from app.models import Funcao, User
    from app.models.enums import RoleEnum, TpaStatusEnum, UserStatusEnum

    funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()
    user = User(
        email=f"match-hit-{secrets.token_hex(3)}@test.local",
        telefone="+5581999990001",
        password_hash=None,
        role=RoleEnum.TPA,
        status=UserStatusEnum.ATIVO,
    )
    db_session.add(user)
    await db_session.flush()
    matricula = "162"
    tpa = Tpa(
        user_id=user.id,
        cpf=f"{secrets.randbelow(10**9):09d}00",
        nome_completo="Matcher Hit",
        matricula_ogmo=matricula,
        telefone="+5581999990001",
        funcao_base_id=funcao.id,
        categoria="TECNICA",
        status_cadastro=TpaStatusEnum.ATIVO,
    )
    db_session.add(tpa)
    await db_session.commit()

    hit = await resolve_tpa_by_matricula(db_session, " 162 ")
    assert hit is not None
    assert hit.id == tpa.id

    miss = await resolve_tpa_by_matricula(db_session, "999")
    assert miss is None


@pytest.mark.asyncio
async def test_load_tpas_by_matriculas_batch(db_session) -> None:
    from app.models import Funcao, User
    from app.models.enums import RoleEnum, TpaStatusEnum, UserStatusEnum

    funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()
    mats = ["100", "200"]
    for i, mat in enumerate(mats):
        user = User(
            email=f"batch-{mat}-{secrets.token_hex(2)}@test.local",
            telefone=f"+55819999900{i:02d}",
            password_hash=None,
            role=RoleEnum.TPA,
            status=UserStatusEnum.ATIVO,
        )
        db_session.add(user)
        await db_session.flush()
        db_session.add(
            Tpa(
                user_id=user.id,
                cpf=f"{secrets.randbelow(10**9):09d}{i:02d}",
                nome_completo=f"Batch {mat}",
                matricula_ogmo=mat,
                telefone=user.telefone or "",
                funcao_base_id=funcao.id,
                categoria="TECNICA",
                status_cadastro=TpaStatusEnum.ATIVO,
            )
        )
    await db_session.commit()

    found = await load_tpas_by_matriculas(db_session, [" 100 ", "200", "404"])
    assert set(found.keys()) == {"100", "200"}
    assert found["100"].matricula_ogmo == "100"
