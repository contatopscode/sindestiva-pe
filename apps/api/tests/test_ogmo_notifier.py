"""SINDESTIVA-PE · Testes do OGMO Notifier (HU005 — notificação + persistência).

Cobre três caminhos do `app.services.ogmo_notifier`:

  1. test_falha_evolution_persiste_falhou — quando o provider externo
     (Evolution API) falha, o `OgmoNotificacao` deve ser persistido com
     `status=FALHOU` + `erro_detalhes` preenchido. Sem persistir o
     erro, perdemos rastro do que aconteceu (o fiscal precisa ver
     "falhou ao enviar" no painel).

  2. test_alias_enviar_endpoint — `enviar_email` é o alias exposto no
     router /remanejamentos/{id}/notificar-ogmo e delega para
     `enviar_notificacao` com canal default WHATSAPP. O teste verifica
     que ambos produzem o mesmo `OgmoNotificacao` (canal=WHATSAPP).

  3. test_invalid_state_retorna_409 — remanejamento em estado
     PENDENTE (não APROVADO) não pode ser notificado → 409 INVALID_STATE.

Total: 3 testes verdes.

Pré-requisito:
  - API live em http://127.0.0.1:8765
  - Catálogos seed (seed_catalogos.py) já populados
  - Manoel Costa (FISCAL) já seedado (seed_users.py)

Fixtures reusadas do `conftest.py`:
  - `api_token_manoel` (FISCAL)
  - `seed_users`
  - `db_session`

Mock: `app.services.evolution.send_text` é patchado com
`unittest.mock.patch` para forçar falha/sucesso sem precisar de rede.
"""
from __future__ import annotations

import secrets
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models import (
    CanalNotificacaoEnum,
    Faina,
    Funcao,
    OgmoNotificacao,
    Porto,
    RoleEnum,
    StatusNotificacaoEnum,
    StatusRemanejamentoEnum,
    Tpa,
    TpaStatusEnum,
    Turno,
    User,
    UserStatusEnum,
)
from app.services.ogmo_notifier import (
    OgmoNotifierError,
    enviar_email,
    enviar_notificacao,
)
from app.services.remanejamento_service import aprovar, criar


# ---------------------------------------------------------------------------
# Helpers locais
# ---------------------------------------------------------------------------


async def _ids_para_remanejamento(db_session) -> dict:
    """Retorna dict com IDs reais (UUIDs) de catálogos + TPA criado.

    Os catálogos vêm do `seed_catalogos.py`; TPA é criado inline.
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

    email = f"tpa-ogmo-{secrets.token_hex(4)}@sindestiva-test.com.br"
    user = User(
        email=email,
        telefone="+5581999990600",
        password_hash=hash_password("tpa-ogmo-2026"),
        role=RoleEnum.FISCAL,
        status=UserStatusEnum.ATIVO,
    )
    db_session.add(user)
    await db_session.flush()
    tpa = Tpa(
        user_id=user.id,
        cpf=f"{secrets.randbelow(10**9):09d}00",
        nome_completo="TPA OGMO Teste",
        matricula_ogmo=f"OG-OG-{secrets.token_hex(2).upper()}"[:10],
        telefone="+5581999990600",
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


async def _criar_rem_pendente(db_session, seed_users) -> str:
    """Cria 1 remanejamento (status=PENDENTE) e retorna o ID."""
    ids = await _ids_para_remanejamento(db_session)
    from app.models import Fiscal

    manoel = next(
        u for u in seed_users if u.email == "manoel@sindestiva-pe.com.br"
    )
    fiscal = (
        await db_session.execute(select(Fiscal).where(Fiscal.user_id == manoel.id))
    ).scalar_one()

    rem = await criar(
        db_session,
        fiscal_id=str(fiscal.id),
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
        observacoes="OGMO teste pendente",
        anexo_url=None,
    )
    assert rem.status == StatusRemanejamentoEnum.PENDENTE
    return str(rem.id)


async def _criar_rem_aprovado(db_session, seed_users) -> str:
    """Cria 1 remanejamento, aprova, e retorna o ID."""
    rem_id = await _criar_rem_pendente(db_session, seed_users)
    from app.models import Fiscal

    manoel = next(
        u for u in seed_users if u.email == "manoel@sindestiva-pe.com.br"
    )
    fiscal = (
        await db_session.execute(select(Fiscal).where(Fiscal.user_id == manoel.id))
    ).scalar_one()
    rem = await aprovar(
        db_session,
        remanejamento_id=rem_id,
        fiscal_id=str(fiscal.id),
        observacoes="Aprovado p/ teste OGMO",
    )
    assert rem.status == StatusRemanejamentoEnum.APROVADO
    return str(rem.id)


# ---------------------------------------------------------------------------
# F4 — tests (HU005)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_falha_evolution_persiste_falhou(
    client,
    db_session,
    seed_users,
) -> None:
    """Evolution API falha → OgmoNotificacao persistido com status=FALHOU.

    Mock de `app.services.evolution.send_text` retornando
    `success=False, error='HTTP 500: ...'` simula a falha do provider
    externo. O fluxo esperado:

      1. `_enviar_whatsapp` chama `evolution_send_text` → success=False
      2. `_persist_result` é chamado com `status=StatusNotificacaoEnum.FALHOU`
      3. Linha em `ogmo_notificacoes` é criada com status=FALHOU +
         `erro_detalhes` preenchido + `falhou_at` setado.

    Por que importa? Sem persistir o erro, o fiscal olharia o painel
    e veria "nada aconteceu" — perderíamos o rastro da falha. O
    trigger `tg_audit_block_update/delete` em ogmo_notificacoes (na
    migration) garante que esse registro é imutável depois.
    """
    rem_id = await _criar_rem_aprovado(db_session, seed_users)

    # Patch em `app.services.ogmo_notifier.evolution_send_text` (que é
    # importado como `from app.services.evolution import send_text`).
    # O caminho que importa pra `_enviar_whatsapp` é o que recebe o
    # patch — por isso patch direto na referência local.
    erro_msg = "HTTP 503: upstream indisponível"
    with patch(
        "app.services.ogmo_notifier.evolution_send_text",
        new=AsyncMock(
            return_value={
                "success": False,
                "provider_id": None,
                "error": erro_msg,
            }
        ),
    ):
        notif = await enviar_email(db_session, remanejamento_id=rem_id)

    # Assert — OgmoNotificacao persistido com FALHOU + erro
    assert notif.status == StatusNotificacaoEnum.FALHOU
    assert notif.erro_detalhes is not None
    assert "503" in notif.erro_detalhes or erro_msg in notif.erro_detalhes
    assert notif.falhou_at is not None  # timestamp da falha foi gravado
    assert notif.enviado_at is None     # não houve envio bem-sucedido
    # Canal WHATSAPP é o default do alias.
    assert notif.canal == CanalNotificacaoEnum.WHATSAPP
    # Reload do banco pra confirmar que a linha realmente foi commitada.
    stmt = select(OgmoNotificacao).where(
        OgmoNotificacao.remanejamento_id == rem_id
    )
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) >= 1
    assert rows[0].status == StatusNotificacaoEnum.FALHOU


@pytest.mark.asyncio
async def test_alias_enviar_endpoint(
    client,
    db_session,
    seed_users,
) -> None:
    """`enviar_email` (alias) produz mesmo resultado que `enviar_notificacao`.

    O router /remanejamentos/{id}/notificar-ogmo importa
    `from app.services.ogmo_notifier import OgmoNotifierError, enviar_email`
    e chama `enviar_email(db, remanejamento_id=...)`. Esse teste garante
    que o alias está em paridade com `enviar_notificacao(canal=WHATSAPP)`:

      - Mesma OgmoNotificacao persistida
      - Mesmo canal (WHATSAPP)
      - Mesmo provider_message_id (mockado)

    Setup: 2 remanejamentos aprovados. Um notificado via `enviar_email`,
    outro via `enviar_notificacao(canal=WHATSAPP)`. Comparam os campos.
    """
    rem_id_alias = await _criar_rem_aprovado(db_session, seed_users)
    rem_id_direto = await _criar_rem_aprovado(db_session, seed_users)

    # Mock Evolution API retornando sucesso em ambos.
    with patch(
        "app.services.ogmo_notifier.evolution_send_text",
        new=AsyncMock(
            return_value={
                "success": True,
                "provider_id": "wa-msg-id-alias-001",
                "error": None,
            }
        ),
    ):
        notif_alias = await enviar_email(
            db_session, remanejamento_id=rem_id_alias
        )
        notif_direto = await enviar_notificacao(
            db_session,
            remanejamento_id=rem_id_direto,
            canal=CanalNotificacaoEnum.WHATSAPP,
        )

    # Assert — alias produz mesmo canal + status que a função canônica.
    assert notif_alias.canal == CanalNotificacaoEnum.WHATSAPP
    assert notif_direto.canal == CanalNotificacaoEnum.WHATSAPP
    assert notif_alias.canal == notif_direto.canal
    # Status ENVIADO em ambos.
    assert notif_alias.status == StatusNotificacaoEnum.ENVIADO
    assert notif_direto.status == StatusNotificacaoEnum.ENVIADO
    # O provider_id mockado foi propagado.
    assert notif_alias.provider_message_id == "wa-msg-id-alias-001"
    # O status do remanejamento mudou pra NOTIFICADO_OGMO em ambos.
    from app.models import Remanejamento

    rem_a = (
        await db_session.execute(
            select(Remanejamento).where(Remanejamento.id == rem_id_alias)
        )
    ).scalar_one()
    rem_b = (
        await db_session.execute(
            select(Remanejamento).where(Remanejamento.id == rem_id_direto)
        )
    ).scalar_one()
    assert rem_a.status == StatusRemanejamentoEnum.NOTIFICADO_OGMO
    assert rem_b.status == StatusRemanejamentoEnum.NOTIFICADO_OGMO


@pytest.mark.asyncio
async def test_invalid_state_retorna_409(
    client,
    db_session,
    seed_users,
) -> None:
    """Remanejamento PENDENTE → tentar notificar → 409 INVALID_STATE.

    A função `_get_rem` em `ogmo_notifier.py` valida:
      - status ∈ {APROVADO, NOTIFICADO_OGMO}
    Qualquer outro estado → `OgmoNotifierError(409, 'INVALID_STATE', ...)`.

    Por que importa? Evita notificar OGMO de um remanejamento que ainda
    não foi aprovado pelo fiscal — quebraria o fluxo de SLA e poderia
    causar confusão no OGMO/PE.
    """
    # Arrange — remanejamento PENDENTE (não aprovado)
    rem_id = await _criar_rem_pendente(db_session, seed_users)

    # Mock Evolution API — não deve nem ser chamado (validação vem antes),
    # mas patch serve pra garantir que se for chamado não vai bater rede.
    with patch(
        "app.services.ogmo_notifier.evolution_send_text",
        new=AsyncMock(return_value={"success": True, "provider_id": "x", "error": None}),
    ):
        with pytest.raises(OgmoNotifierError) as excinfo:
            await enviar_email(db_session, remanejamento_id=rem_id)

    # Assert — OgmoNotifierError(409, INVALID_STATE)
    assert excinfo.value.status == 409
    assert excinfo.value.code == "INVALID_STATE"
    assert "PENDENTE" in excinfo.value.message or "esperado" in excinfo.value.message

    # Garante que nenhuma OgmoNotificacao foi criada (validação antes
    # de qualquer persistência).
    stmt = select(OgmoNotificacao).where(
        OgmoNotificacao.remanejamento_id == rem_id
    )
    rows = (await db_session.execute(stmt)).scalars().all()
    assert rows == [], "Nenhuma OgmoNotificacao deveria existir para PENDENTE"