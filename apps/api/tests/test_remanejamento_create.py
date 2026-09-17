"""SINDESTIVA-PE · Testes do POST /remanejamentos (HU001).

Cobre:
  - Happy path: cria com UUIDs reais (Porto/Turno/Funao/Faina/TPA) +
    motivo do enum + status=PENDENTE + codigo_se no formato SE-YYYYMMDD-NNN.
  - 2 cenários de erro 404 (NOT_FOUND):
      * CCT_NOT_FOUND — base_legal_cct_id inexistente
      * TPA_OUT_NOT_FOUND — tpa_out_id inexistente

Total: 3 testes verdes.

Pré-requisito:
  - API live em http://127.0.0.1:8765
  - Catálogos seed (seed_catalogos.py) já populados (Porto/Turno/Funao/Faina)
  - Manoel Costa (FISCAL) já seedado (seed_users.py → perfil Fiscal)

Fixtures reusadas do `conftest.py`:
  - `api_token_manoel` (FISCAL) e `api_token_paulo` (DIRIGENTE + perfil fiscal)
  - `seed_users`
  - `db_session`
"""
from __future__ import annotations

import re
import secrets
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models import (
    Fiscal,
    Funcao,
    Faina,
    Porto,
    RoleEnum,
    Tpa,
    TpaStatusEnum,
    Turno,
    User,
    UserStatusEnum,
)


CODIGO_SE_REGEX = re.compile(r"^SE-\d{8}-\d{3}$")


# ---------------------------------------------------------------------------
# Helpers locais
# ---------------------------------------------------------------------------


async def _primeiro_catalogo(db_session, *, codigo_porto: str = "SUAPE"):
    """Retorna (Porto, Turno, Funcao, Faina) já populados pelo seed.

    Lança se algum catálogo estiver ausente — esse é um sinal de que o
    seed_catalogos.py não foi rodado no ambiente.
    """
    porto = (
        await db_session.execute(select(Porto).where(Porto.codigo == codigo_porto))
    ).scalar_one()
    turno = (
        await db_session.execute(select(Turno).order_by(Turno.codigo).limit(1))
    ).scalar_one()
    funcao = (
        await db_session.execute(select(Funcao).order_by(Funcao.ordem_lousa).limit(1))
    ).scalar_one()
    faina = (
        await db_session.execute(select(Faina).order_by(Faina.ordem_lousa).limit(1))
    ).scalar_one()
    return porto, turno, funcao, faina


async def _ensure_fiscal_paulo(db_session, user: User) -> Fiscal:
    """Garante perfil Fiscal para Paulo (DIRIGENTE) nos testes isolados."""
    from datetime import date  # noqa: PLC0415

    from app.models import FiscalStatusEnum  # noqa: PLC0415

    existing = (
        await db_session.execute(select(Fiscal).where(Fiscal.user_id == user.id))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    porto, turno, _, _ = await _primeiro_catalogo(db_session)
    fiscal = Fiscal(
        user_id=user.id,
        cpf="11122233396",
        nome_completo="Paulo Siqueira",
        matricula_sindicato="FISCAL-DTO-TEST",
        telefone="+5581999990001",
        porto_id=porto.id,
        turno_id=turno.id,
        status=FiscalStatusEnum.ATIVO,
        data_inicio=date.today(),
    )
    db_session.add(fiscal)
    await db_session.commit()
    await db_session.refresh(fiscal)
    return fiscal


async def _criar_tpa(db_session, *, nome: str = "TPA Teste Criar"):
    """Cria User role=FISCAL + Tpa vinculado para servir como `tpa_out_id`.

    TPA em si é role=TPA mas a constraint `ck_users_password_for_non_tpa`
    proíbe password_hash em users TPA. Como só precisamos do Tpa.id
    (sem login), usamos o mesmo padrão do `tpa_user_with_login`:
    User role=FISCAL + Tpa linkado.
    """
    email = f"tpa-criar-{secrets.token_hex(4)}@sindestiva-test.com.br"
    user = User(
        email=email,
        telefone="+5581999990700",
        password_hash=hash_password("tpa-criar-2026"),
        role=RoleEnum.FISCAL,
        status=UserStatusEnum.ATIVO,
    )
    db_session.add(user)
    await db_session.flush()

    funcao = (
        await db_session.execute(select(Funcao).limit(1))
    ).scalar_one()
    tpa = Tpa(
        user_id=user.id,
        cpf=f"{secrets.randbelow(10**9):09d}00",
        nome_completo=nome,
        matricula_ogmo=f"OG-CR-{secrets.token_hex(2).upper()}"[:10],
        telefone="+5581999990700",
        funcao_base_id=funcao.id,
        categoria="TECNICA",
        status_cadastro=TpaStatusEnum.ATIVO,
    )
    db_session.add(tpa)
    await db_session.commit()
    await db_session.refresh(tpa)
    return tpa


# ---------------------------------------------------------------------------
# F2 — tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_criar_com_uuids_reais_e_motivo_enum(
    client,
    db_session,
    seed_users,
    api_token_manoel,
) -> None:
    """POST /remanejamentos com UUIDs reais + motivo ATESTADO_MEDICO → 201.

    Valida:
      - status == 'PENDENTE'
      - codigo_se no formato `SE-YYYYMMDD-NNN` (gerado pelo trigger)
      - id é UUID válido
      - payload ecoa motivo como 'ATESTADO_MEDICO' (valor do enum)
    """
    # Arrange — pegar catálogos seed + criar TPA
    porto, turno, funcao, faina = await _primeiro_catalogo(db_session)
    tpa_out = await _criar_tpa(db_session, nome="TPA Substituído")

    payload = {
        "porto_id": str(porto.id),
        "turno_id": str(turno.id),
        "data_referencia": date.today().isoformat(),
        "tpa_out_id": str(tpa_out.id),
        "funcao_origem_id": str(funcao.id),
        "faina_origem_id": str(faina.id),
        "cais_origem": "Cais 1",
        "motivo": "ATESTADO_MEDICO",
        "motivo_outro_texto": None,
        "observacoes": "Teste HU001 — happy path",
    }

    # Act
    resp = await client.post(
        "/api/v1/remanejamentos",
        json=payload,
        headers={"Authorization": f"Bearer {api_token_manoel}"},
    )

    # Assert
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "PENDENTE"
    assert body["motivo"] == "ATESTADO_MEDICO"
    # codigo_se no formato SE-YYYYMMDD-NNN (gerado por trigger BEFORE INSERT)
    codigo = body["codigo_se"]
    assert CODIGO_SE_REGEX.match(codigo), (
        f"codigo_se fora do formato SE-YYYYMMDD-NNN: {codigo!r}"
    )
    # id é UUID válido
    uuid.UUID(body["id"])
    # tpa_out_id ecoado é o mesmo
    assert body["tpa_out_id"] == str(tpa_out.id)


@pytest.mark.asyncio
async def test_cct_not_found_404(
    client,
    db_session,
    seed_users,
    api_token_manoel,
) -> None:
    """POST com `base_legal_cct_id` inexistente → 404 CCT_NOT_FOUND."""
    porto, turno, funcao, faina = await _primeiro_catalogo(db_session)
    tpa_out = await _criar_tpa(db_session, nome="TPA CCT-404")

    cct_inexistente = str(uuid.uuid4())  # UUID aleatório que não existe no DB

    payload = {
        "porto_id": str(porto.id),
        "turno_id": str(turno.id),
        "data_referencia": date.today().isoformat(),
        "tpa_out_id": str(tpa_out.id),
        "funcao_origem_id": str(funcao.id),
        "faina_origem_id": str(faina.id),
        "motivo": "ATESTADO_MEDICO",
        "base_legal_cct_id": cct_inexistente,
    }

    resp = await client.post(
        "/api/v1/remanejamentos",
        json=payload,
        headers={"Authorization": f"Bearer {api_token_manoel}"},
    )

    assert resp.status_code == 404, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "CCT_NOT_FOUND"
    assert cct_inexistente in detail["message"]


@pytest.mark.asyncio
async def test_tpa_out_not_found_404(
    client,
    db_session,
    seed_users,
    api_token_manoel,
) -> None:
    """POST com `tpa_out_id` inexistente → 404 TPA_OUT_NOT_FOUND."""
    porto, turno, funcao, faina = await _primeiro_catalogo(db_session)
    tpa_inexistente = str(uuid.uuid4())

    payload = {
        "porto_id": str(porto.id),
        "turno_id": str(turno.id),
        "data_referencia": date.today().isoformat(),
        "tpa_out_id": tpa_inexistente,
        "funcao_origem_id": str(funcao.id),
        "faina_origem_id": str(faina.id),
        "motivo": "ATESTADO_MEDICO",
    }

    resp = await client.post(
        "/api/v1/remanejamentos",
        json=payload,
        headers={"Authorization": f"Bearer {api_token_manoel}"},
    )

    assert resp.status_code == 404, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "TPA_OUT_NOT_FOUND"
    assert tpa_inexistente in detail["message"]


@pytest.mark.asyncio
async def test_dirigente_com_perfil_fiscal_pode_criar(
    client,
    db_session,
    seed_users,
    api_token_paulo,
) -> None:
    """DIRIGENTE (Paulo) com perfil Fiscal seedado → POST 201 (HOM smoke)."""
    from app.models import User  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    user = (
        await db_session.execute(
            select(User).where(User.email == "paulo@pscode.ia.br")
        )
    ).scalar_one()
    await _ensure_fiscal_paulo(db_session, user)

    porto, turno, funcao, faina = await _primeiro_catalogo(db_session)
    tpa_out = await _criar_tpa(db_session, nome="TPA Dirigente Create")

    payload = {
        "porto_id": str(porto.id),
        "turno_id": str(turno.id),
        "data_referencia": date.today().isoformat(),
        "tpa_out_id": str(tpa_out.id),
        "funcao_origem_id": str(funcao.id),
        "faina_origem_id": str(faina.id),
        "motivo": "ATESTADO_MEDICO",
    }

    resp = await client.post(
        "/api/v1/remanejamentos",
        json=payload,
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "PENDENTE"