"""SINDESTIVA-PE · Testes do GET /remanejamentos (HU002 — paginação).

Cobre a listagem paginada via `GET /api/v1/remanejamentos?skip=0&limit=2`:
  - Cria 3 remanejamentos via `service.criar` (não via HTTP — teste
    direto no service pra simplificar o setup).
  - Faz GET com `skip=0&limit=2` via API live.
  - Espera 200 + items.length === 2 + total === 3 (todos os 3
    remanejamentos existem no DB, mas só 2 são retornados pela página).

Por que o `total=3` (não 2)?
    A paginação `skip/limit` afeta o tamanho da página retornada, mas
    `total` é a contagem total de registros — independe de paginação.
    Esse é o contrato do `RemanejamentoListResponse`.

Total: 1 teste verde.

Pré-requisito:
  - API live em http://127.0.0.1:8765
  - Catálogos seed (seed_catalogos.py) já populados
  - Manoel Costa (FISCAL) já seedado

Fixtures reusadas do `conftest.py`:
  - `api_token_manoel` (FISCAL)
  - `seed_users`
  - `db_session`
"""
from __future__ import annotations

import secrets
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models import (
    Faina,
    Funcao,
    Porto,
    RoleEnum,
    Tpa,
    TpaStatusEnum,
    Turno,
    User,
    UserStatusEnum,
)
from app.services.remanejamento_service import criar


# ---------------------------------------------------------------------------
# Helpers locais
# ---------------------------------------------------------------------------


async def _setup_catalogo_e_tpa(db_session) -> dict:
    """Retorna dict com IDs reais (UUIDs) dos catálogos + TPA criado.

    Todos os catálogos já estão populados via `seed_catalogos.py`.
    O TPA é criado inline (mesmo padrão do `test_remanejamento_create`).
    """
    porto = (
        await db_session.execute(select(Porto).where(Porto.codigo == "SUAPE"))
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

    email = f"tpa-list-{secrets.token_hex(4)}@sindestiva-test.com.br"
    user = User(
        email=email,
        telefone="+5581999990800",
        password_hash=hash_password("tpa-list-2026"),
        role=RoleEnum.FISCAL,
        status=UserStatusEnum.ATIVO,
    )
    db_session.add(user)
    await db_session.flush()
    tpa = Tpa(
        user_id=user.id,
        cpf=f"{secrets.randbelow(10**9):09d}00",
        nome_completo="TPA Lista",
        matricula_ogmo=f"OG-LS-{secrets.token_hex(2).upper()}"[:10],
        telefone="+5581999990800",
        funcao_base_id=funcao.id,
        categoria="TECNICA",
        status_cadastro=TpaStatusEnum.ATIVO,
    )
    db_session.add(tpa)
    await db_session.commit()
    await db_session.refresh(tpa)

    return {
        "porto_id": str(porto.id),
        "turno_id": str(turno.id),
        "funcao_origem_id": str(funcao.id),
        "faina_origem_id": str(faina.id),
        "tpa_out_id": str(tpa.id),
    }


# ---------------------------------------------------------------------------
# F3 — tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_listar_paginado(
    client,
    db_session,
    seed_users,
    api_token_manoel,
) -> None:
    """Cria 3 remanejamentos via service.criar → GET /remanejamentos paginado.

    Setup:
      1. Pega catálogos + cria TPA.
      2. Para cada remanejamento (i=0..2), chama `service.criar` com
         `data_referencia` diferente (pra evitar duplicação em campos
         que não têm UNIQUE aqui, mas principalmente pra criar 3 linhas
         com `created_at` distintos — o ORDER BY da listagem é por
         `created_at DESC`, então a ordem dos itens reflete a inserção).
    Assert:
      - GET /remanejamentos?skip=0&limit=2 → 200
      - items.length === 2 (paginação)
      - total === 3 (contagem total)
    """
    # Arrange — preparar catálogos + TPA
    ids = await _setup_catalogo_e_tpa(db_session)

    # Manoel é o fiscal logado (api_token_manoel). Precisamos do
    # manoel_user.id para passar `fiscal_id` ao service.criar — mas o
    # helper `criar` espera `fiscal_id` (FK pra `fiscais.id`), não
    # `user_id`. Buscamos via seed_users.
    manoel = next(
        u for u in seed_users if u.email == "manoel@sindestiva-pe.com.br"
    )
    # Manoel já tem perfil Fiscal criado pelo seed_users.py (1:1 com
    # user.id). Buscar o fiscal_id.
    from app.models import Fiscal

    fiscal = (
        await db_session.execute(
            select(Fiscal).where(Fiscal.user_id == manoel.id)
        )
    ).scalar_one()
    fiscal_id = str(fiscal.id)

    # Criar 3 remanejamentos via service (datas diferentes)
    base = date.today()
    for offset in range(3):
        rem = await criar(
            db_session,
            fiscal_id=fiscal_id,
            tpa_out_id=ids["tpa_out_id"],
            tpa_in_id=None,
            motivo="ATESTADO_MEDICO",
            motivo_outro_texto=None,
            funcao_origem_id=ids["funcao_origem_id"],
            faina_origem_id=ids["faina_origem_id"],
            porto_id=ids["porto_id"],
            turno_id=ids["turno_id"],
            data_referencia=base + timedelta(days=offset),
            cais_origem=f"Cais {offset + 1}",
            base_legal_cct_id=None,
            base_legal_texto_livre=None,
            observacoes=f"Teste list {offset + 1}",
            anexo_url=None,
        )
        # `criar` já faz commit internamente; só mantemos referência.
        assert rem.codigo_se.startswith("SE-")

    # Act — GET paginado via API live
    resp = await client.get(
        "/api/v1/remanejamentos?skip=0&limit=2",
        headers={"Authorization": f"Bearer {api_token_manoel}"},
    )

    # Assert
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "skip" in body
    assert "limit" in body
    assert body["skip"] == 0
    assert body["limit"] == 2
    # Paginação: 2 itens retornados, mas o total é 3.
    assert len(body["items"]) == 2
    assert body["total"] == 3