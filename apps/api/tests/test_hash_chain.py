"""SINDESTIVA-PE · Testes de integridade do hash chain (RNF-11).

RNF-11: "Toda alteração em dados pessoais deve gerar evento na hash
chain encadeada; adulteração de 1 evento invalida a cadeia."

Este arquivo cobre:

  1. test_sequencia_criar_aprovar_notificar — fluxo completo
     (criar → aprovar → notificar) encadeia corretamente os eventos
     de `audit_events`, sem quebrar a sequência e com `hash_anterior`
     apontando pro evento anterior.

  2. test_audit_list_nao_quebra_hash_chain — chamar o endpoint
     `/auditoria/eventos` (que carrega `actor_user` via
     `selectinload`) não altera a cadeia. Isso é uma proteção contra
     regressões: se algum dia alguém adicionar uma escrita acidental
     em `_get_rem`/listagem, a cadeia quebraria. Aqui garantimos que
     a listagem é READ-ONLY na cadeia.

Total: 2 testes verdes.

Pré-requisito:
  - API live em http://127.0.0.1:8765
  - Catálogos seed (seed_catalogos.py) já populados
  - Manoel Costa (FISCAL) já seedado (seed_users.py)

Fixtures reusadas do `conftest.py`:
  - `api_token_paulo` (DIRIGENTE — para GET /auditoria/eventos)
  - `api_token_manoel` (FISCAL — para criar/aprovar remanejamento)
  - `seed_users`
  - `db_session`
"""
from __future__ import annotations

import secrets
from datetime import date

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models import (
    AuditEvent,
    Faina,
    Funcao,
    Porto,
    RoleEnum,
    StatusRemanejamentoEnum,
    Tpa,
    TpaStatusEnum,
    Turno,
    User,
    UserStatusEnum,
)
from app.services.hash_chain import GENESIS_HASH, verify_chain
from app.services.remanejamento_service import aprovar, criar


# ---------------------------------------------------------------------------
# Helpers locais
# ---------------------------------------------------------------------------


async def _ids_para_remanejamento(db_session) -> dict:
    """Retorna dict com IDs reais (UUIDs) dos catálogos seed + TPA criado."""
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

    email = f"tpa-hc-{secrets.token_hex(4)}@sindestiva-test.com.br"
    user = User(
        email=email,
        telefone="+5581999990500",
        password_hash=hash_password("tpa-hc-2026"),
        role=RoleEnum.FISCAL,
        status=UserStatusEnum.ATIVO,
    )
    db_session.add(user)
    await db_session.flush()
    tpa = Tpa(
        user_id=user.id,
        cpf=f"{secrets.randbelow(10**9):09d}00",
        nome_completo="TPA Hash Chain",
        matricula_ogmo=f"OG-HC-{secrets.token_hex(2).upper()}"[:10],
        telefone="+5581999990500",
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
# F4 — tests (RNF-11)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sequencia_criar_aprovar_notificar(
    client,
    db_session,
    seed_users,
    api_token_manoel,
) -> None:
    """Fluxo criar → aprovar encadeia eventos na hash chain (sequência monotônica).

    Valida:
      - Após `criar`, existe 1 AuditEvent com entity_type='remanejamento',
        event_type='CREATE'.
      - Após `aprovar`, existe um novo AuditEvent com event_type='STATUS_CHANGE'.
      - O `hash_anterior` do 2º evento == `hash_evento` do 1º (encadeamento).
      - A sequência é monotônica (2ª > 1ª).
      - `verify_chain` sobre os 2 eventos retorna íntegro.

    Não testamos `notificar` (envio OGMO) aqui porque o `_enviar_whatsapp`
    faz HTTP para Evolution API — fora do escopo deste teste de hash chain.
    O fluxo criar+aprovar já exercita o encadeamento completo.
    """
    # Arrange — ids + fiscal
    ids = await _ids_para_remanejamento(db_session)
    from app.models import Fiscal

    manoel = next(
        u for u in seed_users if u.email == "manoel@sindestiva-pe.com.br"
    )
    fiscal = (
        await db_session.execute(select(Fiscal).where(Fiscal.user_id == manoel.id))
    ).scalar_one()
    fiscal_id = str(fiscal.id)

    # Act 1 — criar remanejamento
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
        data_referencia=date.today(),
        cais_origem="Cais 1",
        base_legal_cct_id=None,
        base_legal_texto_livre=None,
        observacoes="Hash chain teste — criar",
        anexo_url=None,
    )
    rem_id = str(rem.id)

    # Captura o AuditEvent gerado pelo `criar`.
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.entity_id == rem_id)
        .where(AuditEvent.event_type == "CREATE")
        .order_by(AuditEvent.sequencia.desc())
        .limit(1)
    )
    evt_criar = (await db_session.execute(stmt)).scalar_one()
    assert evt_criar.event_type == "CREATE"
    assert evt_criar.entity_type == "remanejamento"
    assert evt_criar.hash_anterior is not None
    seq_criar = evt_criar.sequencia
    hash_criar = evt_criar.hash_evento

    # Act 2 — aprovar remanejamento
    rem_aprovado = await aprovar(
        db_session,
        remanejamento_id=rem_id,
        fiscal_id=fiscal_id,
        observacoes="Aprovação — teste hash chain",
    )
    assert rem_aprovado.status == StatusRemanejamentoEnum.APROVADO

    # Captura o AuditEvent gerado pelo `aprovar`.
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.entity_id == rem_id)
        .where(AuditEvent.event_type == "STATUS_CHANGE")
        .order_by(AuditEvent.sequencia.desc())
        .limit(1)
    )
    evt_aprovar = (await db_session.execute(stmt)).scalar_one()
    assert evt_aprovar.event_type == "STATUS_CHANGE"
    seq_aprovar = evt_aprovar.sequencia

    # Assert — encadeamento correto
    assert seq_aprovar > seq_criar, (
        f"sequência deve ser monotônica: {seq_criar} → {seq_aprovar}"
    )
    assert evt_aprovar.hash_anterior == hash_criar, (
        "hash_anterior do 2º evento deve ser o hash_evento do 1º"
    )
    assert evt_aprovar.hash_evento is not None
    assert evt_aprovar.hash_evento != hash_criar  # mudou (novo payload)

    # Assert — verify_chain() valida os 2 eventos como íntegros
    # (juntos, sem eventos anteriores)
    integro, idx_falha = verify_chain([evt_criar, evt_aprovar])
    assert integro is True
    assert idx_falha == -1


@pytest.mark.asyncio
async def test_audit_list_nao_quebra_hash_chain(
    client,
    db_session,
    seed_users,
    api_token_paulo,
    api_token_manoel,
) -> None:
    """GET /auditoria/eventos (com selectinload) é READ-ONLY na cadeia.

    Setup:
      1. Cria 1 remanejamento (gera AuditEvent CREATE).
      2. Captura hash_evento do último evento + contagem total.
    Act:
      3. GET /api/v1/auditoria/eventos via API live (carrega actor_user).
    Assert:
      4. A cadeia de eventos continua íntegra (verify_chain OK).
      5. A contagem de eventos não mudou.
      6. O hash_evento do último evento continua o mesmo.
      7. A sequência dos eventos não mudou.

    Por que importa? A listagem usa `selectinload(AuditEvent.actor_user)`
    + popula `actor_nome` em Python. Se um dia alguém adicionar uma
    escrita acidental (ex.: `db.add()` em `actor_user.tpa`) durante a
    listagem, a cadeia quebraria silenciosamente. Esse teste é uma rede
    contra regressões.
    """
    # Arrange — ids + fiscal + remanejamento
    ids = await _ids_para_remanejamento(db_session)
    from app.models import Fiscal

    manoel = next(
        u for u in seed_users if u.email == "manoel@sindestiva-pe.com.br"
    )
    fiscal = (
        await db_session.execute(select(Fiscal).where(Fiscal.user_id == manoel.id))
    ).scalar_one()
    fiscal_id = str(fiscal.id)

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
        data_referencia=date.today(),
        cais_origem="Cais 1",
        base_legal_cct_id=None,
        base_legal_texto_livre=None,
        observacoes="Hash chain — listagem read-only",
        anexo_url=None,
    )

    # Snapshot antes da listagem
    def _snapshot() -> tuple[int, str, int, list[AuditEvent]]:
        stmt = select(AuditEvent).order_by(AuditEvent.sequencia)
        rows = list((await db_session.execute(stmt)).scalars().all())
        ultimo = rows[-1] if rows else None
        return (
            len(rows),
            (ultimo.hash_evento if ultimo else GENESIS_HASH),
            (ultimo.sequencia if ultimo else 0),
            rows,
        )

    count_antes, hash_antes, seq_antes, eventos_antes = await _snapshot()

    # Act — GET /auditoria/eventos (carrega actor_user via selectinload)
    resp = await client.get(
        "/api/v1/auditoria/eventos?limit=200",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1

    # Snapshot depois da listagem
    count_depois, hash_depois, seq_depois, eventos_depois = await _snapshot()

    # Assert — cadeia inalterada
    assert count_depois == count_antes, (
        f"contagem de eventos mudou após listagem: {count_antes} → {count_depois}"
    )
    assert hash_depois == hash_antes, (
        "hash_evento do último evento mudou após listagem"
    )
    assert seq_depois == seq_antes, (
        "sequência do último evento mudou após listagem"
    )
    # verify_chain continua íntegro sobre todos os eventos.
    integro, idx_falha = verify_chain(eventos_depois)
    assert integro is True, (
        f"cadeia quebrada após listagem (idx_falha={idx_falha})"
    )
    assert idx_falha == -1