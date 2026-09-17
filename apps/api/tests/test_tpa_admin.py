"""SINDESTIVA-PE · Testes gestão admin de TPAs."""

from __future__ import annotations

import secrets
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Funcao, TpaFuncao, User
from app.models.enums import UserStatusEnum
from scripts.seed_catalogos import seed as seed_catalogos


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _funcao_tecnica(db_session: AsyncSession) -> Funcao:
    await seed_catalogos()
    funcao = (
        await db_session.execute(select(Funcao).where(Funcao.codigo == "TECNICA_01"))
    ).scalar_one()
    return funcao


async def _funcao_by_codigo(db_session: AsyncSession, codigo: str) -> Funcao:
    await seed_catalogos()
    return (
        await db_session.execute(select(Funcao).where(Funcao.codigo == codigo))
    ).scalar_one()


def _unique_cpf() -> str:
    return f"{secrets.randbelow(10**9):09d}{secrets.randbelow(100):02d}"[:11]


@pytest.mark.asyncio
async def test_tpas_list_200_fiscal(client, seed_users, api_token_manoel) -> None:
    resp = await client.get("/api/v1/tpas", headers=_auth(api_token_manoel))
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_tpas_list_403_tpa_role(client, seed_users, api_token_tpa) -> None:
    resp = await client.get("/api/v1/tpas", headers=_auth(api_token_tpa))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ROLE_REQUIRED"


@pytest.mark.asyncio
async def test_tpas_fiscal_create_two_funcoes(
    client,
    seed_users,
    db_session,
    api_token_manoel,
) -> None:
    f1 = await _funcao_by_codigo(db_session, "TECNICA_01")
    f2 = await _funcao_by_codigo(db_session, "TECNICA_02")
    cpf = _unique_cpf()
    payload = {
        "cpf": cpf,
        "nome_completo": "TPA Multifunção Fiscal",
        "matricula_ogmo": secrets.token_hex(2)[:8],
        "telefone": "+5581987000010",
        "funcao_ids": [str(f1.id), str(f2.id)],
        "funcao_base_id": str(f1.id),
        "status_cadastro": "ATIVO",
    }
    create = await client.post(
        "/api/v1/tpas", json=payload, headers=_auth(api_token_manoel)
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert len(body["funcoes"]) == 2
    ids = {f["id"] for f in body["funcoes"]}
    assert str(f1.id) in ids and str(f2.id) in ids
    assert body["funcao_base_id"] == str(f1.id)

    links = (
        await db_session.execute(
            select(TpaFuncao).where(TpaFuncao.tpa_id == UUID(body["id"]))
        )
    ).scalars().all()
    assert len(links) == 2


@pytest.mark.asyncio
async def test_tpas_funcao_base_not_in_set_422(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    f1 = await _funcao_by_codigo(db_session, "TECNICA_01")
    f2 = await _funcao_by_codigo(db_session, "TECNICA_02")
    f3 = await _funcao_by_codigo(db_session, "TECNICA_03")
    resp = await client.post(
        "/api/v1/tpas",
        json={
            "cpf": _unique_cpf(),
            "nome_completo": "Base Inválida",
            "matricula_ogmo": "BAS001",
            "telefone": "+5581987000011",
            "funcao_ids": [str(f1.id), str(f2.id)],
            "funcao_base_id": str(f3.id),
        },
        headers=_auth(api_token_paulo),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "FUNCAO_BASE_NOT_IN_SET"


@pytest.mark.asyncio
async def test_tpas_update_sync_funcoes(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    f1 = await _funcao_by_codigo(db_session, "TECNICA_01")
    f2 = await _funcao_by_codigo(db_session, "TECNICA_02")
    f3 = await _funcao_by_codigo(db_session, "TECNICA_03")
    create = await client.post(
        "/api/v1/tpas",
        json={
            "cpf": _unique_cpf(),
            "nome_completo": "Sync Funções",
            "matricula_ogmo": secrets.token_hex(2),
            "telefone": "+5581987000012",
            "funcao_ids": [str(f1.id)],
        },
        headers=_auth(api_token_paulo),
    )
    assert create.status_code == 201
    tpa_id = create.json()["id"]

    patch = await client.patch(
        f"/api/v1/tpas/{tpa_id}",
        json={"funcao_ids": [str(f2.id), str(f3.id)]},
        headers=_auth(api_token_paulo),
    )
    assert patch.status_code == 200
    body = patch.json()
    assert len(body["funcoes"]) == 2
    assert body["funcao_base_id"] == str(f2.id)


@pytest.mark.asyncio
async def test_tpas_create_get_password_null(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    funcao = await _funcao_tecnica(db_session)
    cpf = _unique_cpf()
    matricula = secrets.token_hex(3)[:8]
    payload = {
        "cpf": cpf,
        "nome_completo": "TPA Admin Teste",
        "matricula_ogmo": matricula,
        "telefone": "+5581987000001",
        "funcao_base_id": str(funcao.id),
        "status_cadastro": "ATIVO",
    }
    create = await client.post(
        "/api/v1/tpas", json=payload, headers=_auth(api_token_paulo)
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["cpf"] == cpf
    assert body["email"] == f"tpa+{cpf}@sindestiva.local"
    assert len(body["funcoes"]) >= 1
    tpa_id = body["id"]

    user = (
        await db_session.execute(select(User).where(User.id == UUID(body["user_id"])))
    ).scalar_one()
    assert user.password_hash is None
    assert user.role.value == "TPA"

    get_resp = await client.get(
        f"/api/v1/tpas/{tpa_id}", headers=_auth(api_token_paulo)
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["matricula_ogmo"] == matricula


@pytest.mark.asyncio
async def test_tpas_duplicate_cpf_matricula_409(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    funcao = await _funcao_tecnica(db_session)
    cpf = _unique_cpf()
    matricula = secrets.token_hex(2)[:6].upper()
    base = {
        "cpf": cpf,
        "nome_completo": "Dup TPA",
        "matricula_ogmo": matricula,
        "telefone": "+5581987000002",
        "funcao_base_id": str(funcao.id),
    }
    first = await client.post("/api/v1/tpas", json=base, headers=_auth(api_token_paulo))
    assert first.status_code == 201

    dup_cpf = await client.post(
        "/api/v1/tpas",
        json={**base, "matricula_ogmo": secrets.token_hex(2)[:6].upper()},
        headers=_auth(api_token_paulo),
    )
    assert dup_cpf.status_code == 409
    assert dup_cpf.json()["detail"]["code"] == "CPF_DUPLICATE"

    dup_mat = await client.post(
        "/api/v1/tpas",
        json={**base, "cpf": _unique_cpf(), "matricula_ogmo": matricula},
        headers=_auth(api_token_paulo),
    )
    assert dup_mat.status_code == 409
    assert dup_mat.json()["detail"]["code"] == "MATRICULA_DUPLICATE"


@pytest.mark.asyncio
async def test_tpas_invalid_matricula_422(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    funcao = await _funcao_tecnica(db_session)
    base = {
        "cpf": _unique_cpf(),
        "nome_completo": "Mat Inválida",
        "telefone": "+5581987000003",
        "funcao_base_id": str(funcao.id),
    }
    long_mat = await client.post(
        "/api/v1/tpas",
        json={**base, "matricula_ogmo": "12345678901"},
        headers=_auth(api_token_paulo),
    )
    assert long_mat.status_code == 422

    comma_mat = await client.post(
        "/api/v1/tpas",
        json={**base, "matricula_ogmo": "1,2"},
        headers=_auth(api_token_paulo),
    )
    assert comma_mat.status_code == 422


@pytest.mark.asyncio
async def test_tpas_patch_status_mirrors_user(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    funcao = await _funcao_tecnica(db_session)
    cpf = _unique_cpf()
    create = await client.post(
        "/api/v1/tpas",
        json={
            "cpf": cpf,
            "nome_completo": "Status Mirror",
            "matricula_ogmo": secrets.token_hex(2),
            "telefone": "+5581987000004",
            "funcao_base_id": str(funcao.id),
            "status_cadastro": "ATIVO",
        },
        headers=_auth(api_token_paulo),
    )
    assert create.status_code == 201
    tpa_id = create.json()["id"]
    user_id = create.json()["user_id"]

    off = await client.patch(
        f"/api/v1/tpas/{tpa_id}",
        json={"status_cadastro": "DESLIGADO"},
        headers=_auth(api_token_paulo),
    )
    assert off.status_code == 200
    assert off.json()["user_status"] == "INATIVO"

    user = (
        await db_session.execute(select(User).where(User.id == UUID(user_id)))
    ).scalar_one()
    assert user.status == UserStatusEnum.INATIVO

    on = await client.patch(
        f"/api/v1/tpas/{tpa_id}",
        json={"status_cadastro": "ATIVO"},
        headers=_auth(api_token_paulo),
    )
    assert on.status_code == 200
    assert on.json()["user_status"] == "ATIVO"


@pytest.mark.asyncio
async def test_tpas_invalid_funcao_422(
    client,
    seed_users,
    api_token_paulo,
) -> None:
    fake_funcao = "00000000-0000-4000-8000-000000000099"
    resp = await client.post(
        "/api/v1/tpas",
        json={
            "cpf": _unique_cpf(),
            "nome_completo": "Sem Função",
            "matricula_ogmo": "NF001",
            "telefone": "+5581987000005",
            "funcao_base_id": fake_funcao,
        },
        headers=_auth(api_token_paulo),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "FUNCAO_INVALIDA"
