"""SINDESTIVA-PE · Testes gestão admin de users (FISCAL + DIRIGENTE)."""
from __future__ import annotations

import secrets
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dirigente, Fiscal, Porto, Turno, User
from scripts.seed_catalogos import seed as seed_catalogos


async def _ensure_internos_profiles(db_session: AsyncSession, users: list[User]) -> None:
    """Garante perfis Fiscal/Dirigente nos 3 users seed (rerun-safe)."""
    porto = (await db_session.execute(select(Porto).where(Porto.codigo == "SUAPE"))).scalar_one()
    turno = (await db_session.execute(select(Turno).where(Turno.codigo == "DIURNO"))).scalar_one()
    today = datetime.now(tz=UTC).date()

    by_email = {u.email: u for u in users}
    manoel = by_email["manoel@sindestiva-pe.com.br"]
    stmt = select(Fiscal).where(Fiscal.user_id == manoel.id)
    fiscal = (await db_session.execute(stmt)).scalar_one_or_none()
    if fiscal is None:
        fiscal = Fiscal(
            user_id=manoel.id,
            cpf="22233344485",
            nome_completo="Manoel Costa",
            matricula_sindicato="FISCAL-001",
            telefone="+5581999990002",
            porto_id=porto.id,
            turno_id=turno.id,
            data_inicio=today,
        )
        db_session.add(fiscal)

    for email, nome, cpf, matricula in (
        ("paulo@pscode.ia.br", "Paulo Siqueira", "11122233396", "DIR-PAULO"),
        ("josias@sindestiva-pe.com.br", "Josias Martins Santiago", "33344455574", "DIR-JOSIAS"),
    ):
        user = by_email[email]
        stmt = select(Dirigente).where(Dirigente.user_id == user.id)
        dirigente = (await db_session.execute(stmt)).scalar_one_or_none()
        if dirigente is None:
            dirigente = Dirigente(
                user_id=user.id,
                cpf=cpf,
                nome_completo=nome,
                cargo="Dirigente",
                matricula_sindicato=matricula,
                data_inicio_mandato=today,
            )
            db_session.add(dirigente)

    await db_session.commit()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_users_list_dirigente(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    await seed_catalogos()
    await _ensure_internos_profiles(db_session, seed_users)
    resp = await client.get("/api/v1/users", headers=_auth(api_token_paulo))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) >= 3
    roles = {item["role"] for item in body["items"]}
    assert "FISCAL" in roles
    assert "DIRIGENTE" in roles
    for item in body["items"]:
        assert "password_hash" not in item
        assert "password" not in item


@pytest.mark.asyncio
async def test_users_list_403_fiscal(client, seed_users, api_token_manoel) -> None:
    resp = await client.get("/api/v1/users", headers=_auth(api_token_manoel))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ROLE_REQUIRED"


@pytest.mark.asyncio
async def test_users_create_fiscal_login(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    await seed_catalogos()
    suffix = secrets.token_hex(3)
    email = f"fiscal-{suffix}@sindestiva-test.com.br"
    password = "nova-senha-2026"
    cpf = f"{secrets.randbelow(10**9):09d}00"
    payload = {
        "email": email,
        "telefone": "+5581987654321",
        "password": password,
        "role": "FISCAL",
        "status": "ATIVO",
        "cpf": cpf,
        "nome_completo": "Fiscal Teste Admin",
        "matricula_sindicato": f"FIS-{suffix.upper()}",
        "porto_codigo": "SUAPE",
        "turno_codigo": "DIURNO",
    }
    resp = await client.post("/api/v1/users", json=payload, headers=_auth(api_token_paulo))
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["email"] == email
    assert created["role"] == "FISCAL"
    assert created["porto_codigo"] == "SUAPE"
    assert created["turno_codigo"] == "DIURNO"

    listed = await client.get("/api/v1/users", headers=_auth(api_token_paulo))
    assert listed.status_code == 200
    match = next((i for i in listed.json()["items"] if i["email"] == email), None)
    assert match is not None
    assert match["porto_codigo"] == "SUAPE"
    assert match["turno_codigo"] == "DIURNO"

    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text

    dup = await client.post(
        "/api/v1/users",
        json={**payload, "matricula_sindicato": f"FIS-DUP-{suffix}"},
        headers=_auth(api_token_paulo),
    )
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "EMAIL_DUPLICATE"


@pytest.mark.asyncio
async def test_users_deactivate_blocks_login(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    await seed_catalogos()
    suffix = secrets.token_hex(3)
    email = f"dir-{suffix}@sindestiva-test.com.br"
    password = "dir-senha-2026"
    cpf = f"{secrets.randbelow(10**9):09d}01"
    create = await client.post(
        "/api/v1/users",
        json={
            "email": email,
            "telefone": "+5581977777777",
            "password": password,
            "role": "DIRIGENTE",
            "cpf": cpf,
            "nome_completo": "Dirigente Temp",
            "matricula_sindicato": f"DIR-{suffix}",
        },
        headers=_auth(api_token_paulo),
    )
    assert create.status_code == 201
    user_id = create.json()["id"]

    login_ok = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_ok.status_code == 200

    patch = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"status": "INATIVO"},
        headers=_auth(api_token_paulo),
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "INATIVO"

    login_fail = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_fail.status_code == 403
    assert login_fail.json()["detail"]["code"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_users_last_active_dirigente_guard(
    client,
    seed_users,
    db_session,
    api_token_paulo,
    paulo_user,
    josias_user,
) -> None:
    await _ensure_internos_profiles(db_session, seed_users)

    # Deixa só Paulo como DIRIGENTE ativo (Josias inativo).
    off_josias = await client.patch(
        f"/api/v1/users/{josias_user.id}",
        json={"status": "INATIVO"},
        headers=_auth(api_token_paulo),
    )
    assert off_josias.status_code == 200

    block_paulo = await client.patch(
        f"/api/v1/users/{paulo_user.id}",
        json={"status": "INATIVO"},
        headers=_auth(api_token_paulo),
    )
    assert block_paulo.status_code == 409
    assert block_paulo.json()["detail"]["code"] == "LAST_ACTIVE_DIRIGENTE"

    # Restaura Josias para não afetar outros testes.
    await client.patch(
        f"/api/v1/users/{josias_user.id}",
        json={"status": "ATIVO"},
        headers=_auth(api_token_paulo),
    )


@pytest.mark.asyncio
async def test_users_create_dirigente_duplicate_cpf(
    client,
    seed_users,
    db_session,
    api_token_paulo,
) -> None:
    await _ensure_internos_profiles(db_session, seed_users)
    suffix = secrets.token_hex(2)
    resp = await client.post(
        "/api/v1/users",
        json={
            "email": f"dup-cpf-{suffix}@test.com",
            "telefone": "+5581966666666",
            "password": "senha-min-8-ch",
            "role": "DIRIGENTE",
            "cpf": "11122233396",
            "nome_completo": "Dup CPF",
            "matricula_sindicato": f"DIR-DUP-{suffix}",
        },
        headers=_auth(api_token_paulo),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CPF_DUPLICATE"
