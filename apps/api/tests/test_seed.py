"""SINDESTIVA-PE · Testes do seed (Sprint 1 T1-03 + T1-09).

Cobre:
  - seed_catalogos: idempotência (2x execução = mesmo total)
  - seed_users: 3 users criados (Paulo, Manoel, Josias)
  - seed_catalogos: contagem das 26 funções por categoria
    (6 Mando + 6 Terno + 12 Técnica + 2 Vigia)

Total: 3 testes verdes.
"""
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models import Funcao, User
from scripts.seed_catalogos import seed as seed_catalogos


# ---------------------------------------------------------------------------
# 1. Idempotência do seed de catálogos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_catalogos_idempotente(db_session) -> None:
    """Rodar seed_catalogos 2x resulta no mesmo total de linhas.

    O seed usa `INSERT ... ON CONFLICT DO NOTHING` — rodar 2x não
    duplica. Aqui validamos que o `contadores` retornado é igual.
    """
    r1 = await seed_catalogos()
    r2 = await seed_catalogos()

    # Mesmas chaves e mesmos valores.
    assert set(r1.keys()) == set(r2.keys())
    for key in r1:
        if key == "dry_run":
            continue
        assert r1[key] == r2[key], f"{key}: {r1[key]} != {r2[key]}"


# ---------------------------------------------------------------------------
# 2. Seed de users (3 users)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_users_3_users_criados(db_session, seed_users) -> None:
    """3 users seed (Paulo DIRIGENTE, Manoel FISCAL, Josias DIRIGENTE).

    O fixture `seed_users` (conftest) já cria os 3. Aqui validamos
    que Paulo/Manoel/Josias estão lá, com role e senha esperada.
    """
    assert len(seed_users) == 3
    by_email = {u.email: u for u in seed_users}

    assert "paulo@pscode.ia.br" in by_email
    assert by_email["paulo@pscode.ia.br"].role.value == "DIRIGENTE"
    assert "manoel@sindestiva-pe.com.br" in by_email
    assert by_email["manoel@sindestiva-pe.com.br"].role.value == "FISCAL"
    assert "josias@sindestiva-pe.com.br" in by_email
    assert by_email["josias@sindestiva-pe.com.br"].role.value == "DIRIGENTE"

    # Senhas bcrypt (não nulas, 60 chars).
    for u in seed_users:
        assert u.password_hash is not None
        assert len(u.password_hash) == 60  # bcrypt 12 rounds
        assert u.password_hash.startswith("$2b$12$")


# ---------------------------------------------------------------------------
# 3. Contagem de funções por categoria
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_catalogos_funcoes_26(
    db_session, seed_users
) -> None:
    """Seed de funções: 6 Mando + 6 Terno + 12 Técnica + 2 Vigia = 26.

    Manoel Costa ainda não confirmou os nomes finais (TODO D5), mas
    o total deve ser 26 e a distribuição por categoria deve bater.
    """
    # Garante que o seed rodou (idempotente).
    await seed_catalogos()

    stmt = select(Funcao.categoria, func.count()).group_by(Funcao.categoria)
    rows = (await db_session.execute(stmt)).all()
    por_categoria = {categoria: count for categoria, count in rows}

    assert por_categoria.get("MANDO", 0) == 6
    assert por_categoria.get("TERNO", 0) == 6
    assert por_categoria.get("TECNICA", 0) == 12
    assert por_categoria.get("VIGIA", 0) == 2
    assert sum(por_categoria.values()) == 26
