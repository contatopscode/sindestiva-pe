"""SINDESTIVA-PE · Testes do /auditoria (HU006 — actor_nome + orfão).

Cobre o carregamento do nome do ator via `selectinload(AuditEvent.actor_user)`
e o fallback para `AuditEvent.actor_user_id IS NULL` (orfão — sem user
associado). Garante o preenchimento de `actor_nome` e `actor_user_email`
em ambos os caminhos:

  - TPA vinculado       → `actor_nome = tpa.nome_completo`
  - AuditEvent orfão    → `actor_nome = None`, `actor_user_email = None`

Total: 2 testes verdes.

Pré-requisito: API live em http://127.0.0.1:8765 (briefing).

Fixtures reusadas do `conftest.py`:
  - `api_token_paulo` (DIRIGENTE)
  - `seed_users` (Paulo/Manoel/Josias)
  - `db_session` (function scope + cleanup explícito)
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models import (
    AuditEvent,
    Funcao,
    RoleEnum,
    Tpa,
    TpaStatusEnum,
    User,
    UserStatusEnum,
)
from app.services.hash_chain import GENESIS_HASH, compute_hash


# ---------------------------------------------------------------------------
# Helpers locais
# ---------------------------------------------------------------------------


async def _criar_user_tpa(
    db_session,
    *,
    email: str | None = None,
    nome_completo: str = "TPA Auditoria",
) -> tuple[User, Tpa]:
    """Cria User role=FISCAL (escapa ck_users_password_for_non_tpa) + Tpa.

    O endpoint /auditoria carrega `actor_user` via `selectinload` e chama
    `resolver_actor_nome(ev.actor_user)`. Quando o user tem `tpa`
    vinculado, o helper retorna `(tpa.nome_completo, user.email)` — é o
    caminho que HU006 documenta como padrão.
    """
    if email is None:
        email = f"tpa-auditoria-{secrets.token_hex(4)}@sindestiva-test.com.br"

    stmt = select(User).where(User.email == email)
    user = (await db_session.execute(stmt)).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            telefone="+5581999990900",
            password_hash=hash_password("tpa-auditoria-2026"),
            role=RoleEnum.FISCAL,
            status=UserStatusEnum.ATIVO,
            accepted_terms_at=datetime.now(tz=timezone.utc),
            accepted_terms_version="1.0",
        )
        db_session.add(user)
        await db_session.flush()
    else:
        user.password_hash = hash_password("tpa-auditoria-2026")
        user.status = UserStatusEnum.ATIVO

    stmt_t = select(Tpa).where(Tpa.user_id == user.id)
    tpa = (await db_session.execute(stmt_t)).scalar_one_or_none()
    if tpa is None:
        funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()
        # CPF 11 dígitos — passa o CHECK de tamanho mas não é válido
        # formalmente (checksum). É o mesmo padrão usado em
        # `tpa_user_with_login` do conftest.
        tpa = Tpa(
            user_id=user.id,
            cpf=f"{secrets.randbelow(10**9):09d}00",
            nome_completo=nome_completo,
            matricula_ogmo=f"OG-AUD-{secrets.token_hex(2).upper()}"[:10],
            telefone="+5581999990900",
            funcao_base_id=funcao.id,
            categoria="TECNICA",
            status_cadastro=TpaStatusEnum.ATIVO,
        )
        db_session.add(tpa)
        await db_session.flush()

    await db_session.commit()
    await db_session.refresh(user)
    return user, tpa


async def _proxima_sequencia(db_session) -> int:
    """Próximo `sequencia` para AuditEvent (sequence do banco + fallback)."""
    stmt = select(AuditEvent.sequencia).order_by(AuditEvent.sequencia.desc()).limit(1)
    result = await db_session.execute(stmt)
    ultimo = result.scalar_one_or_none()
    return (ultimo or 0) + 1


async def _ultimo_hash(db_session) -> str:
    """Último hash_evento da cadeia (ou GENESIS_HASH se vazia)."""
    stmt = select(AuditEvent).order_by(AuditEvent.sequencia.desc()).limit(1)
    result = await db_session.execute(stmt)
    ultimo = result.scalar_one_or_none()
    return ultimo.hash_evento if ultimo else GENESIS_HASH


def _inserir_audit_event(
    db_session,
    *,
    sequencia: int,
    actor_user_id,
    payload_after: dict,
    hash_anterior: str,
) -> AuditEvent:
    """Insere AuditEvent com hash_evento consistente (encadeado)."""
    hash_evento = compute_hash(hash_anterior, payload_after)
    ev = AuditEvent(
        sequencia=sequencia,
        entity_type="test_auditoria",
        entity_id=None,
        event_type="CREATE",
        actor_user_id=actor_user_id,
        actor_role="TPA",
        actor_ip=None,
        actor_user_agent=None,
        payload_before=None,
        payload_after=payload_after,
        metadata_={"origem": "test_auditoria_router"},
        hash_anterior=hash_anterior,
        hash_evento=hash_evento,
        criado_em=datetime.now(tz=timezone.utc),
    )
    db_session.add(ev)
    return ev


# ---------------------------------------------------------------------------
# F1 — tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eventos_traz_actor_nome(
    client,
    db_session,
    seed_users,
    api_token_paulo,
) -> None:
    """AuditEvent com TPA vinculado deve trazer actor_nome + actor_user_email.

    Setup:
      1. Crio User role=FISCAL + Tpa vinculado (TPA-cadastrado).
      2. Insiro AuditEvent apontando actor_user_id = user.id.
    Assert:
      - GET /api/v1/auditoria/eventos → 200
      - O item tem `actor_nome == tpa.nome_completo`
      - O item tem `actor_user_email == user.email`
    """
    # Arrange
    nome_tpa = "TPA Auditavel da Silva"
    user, tpa = await _criar_user_tpa(
        db_session, nome_completo=nome_tpa
    )

    sequencia = await _proxima_sequencia(db_session)
    hash_anterior = await _ultimo_hash(db_session)
    payload = {
        "entity_type": "test_auditoria",
        "actor_user_id": str(user.id),
        "actor_role": "TPA",
        "event_type": "CREATE",
        "sequencia": sequencia,
    }
    _inserir_audit_event(
        db_session,
        sequencia=sequencia,
        actor_user_id=user.id,
        payload_after=payload,
        hash_anterior=hash_anterior,
    )
    await db_session.commit()

    # Act
    resp = await client.get(
        "/api/v1/auditoria/eventos",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )

    # Assert
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1

    # Encontra o item que criamos (pela sequencia única)
    target = next(
        (it for it in items if it.get("sequencia") == sequencia),
        None,
    )
    assert target is not None, (
        f"item com sequencia={sequencia} não retornado em {len(items)} eventos"
    )
    assert target["actor_nome"] == nome_tpa, (
        f"actor_nome esperado={nome_tpa!r} veio={target['actor_nome']!r}"
    )
    assert target["actor_user_email"] == user.email


@pytest.mark.asyncio
async def test_eventos_actor_user_orfao_devolve_none(
    client,
    db_session,
    seed_users,
    api_token_paulo,
) -> None:
    """AuditEvent com `actor_user_id IS NULL` (orfão) → 200 com None/None.

    Setup:
      1. Insiro AuditEvent com actor_user_id=None (sem user FK).
    Assert:
      - GET /api/v1/auditoria/eventos → 200
      - O item tem `actor_nome IS None` e `actor_user_email IS None`.

    Por que importa? Quando user é deletado (LGPD), `users.id` some
    mas `audit_events.actor_user_id` pode ficar NULL (RESTRICT +
    cascade SET NULL?) — o endpoint tem que não quebrar e retornar
    None pros campos opcionais em vez de 500.
    """
    # Arrange
    sequencia = await _proxima_sequencia(db_session)
    hash_anterior = await _ultimo_hash(db_session)
    payload = {
        "entity_type": "test_auditoria",
        "actor_user_id": None,
        "actor_role": None,
        "event_type": "CREATE",
        "sequencia": sequencia,
        "origem": "test_orfao",
    }
    _inserir_audit_event(
        db_session,
        sequencia=sequencia,
        actor_user_id=None,
        payload_after=payload,
        hash_anterior=hash_anterior,
    )
    await db_session.commit()

    # Act
    resp = await client.get(
        "/api/v1/auditoria/eventos",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )

    # Assert
    assert resp.status_code == 200, resp.text
    items = resp.json()
    target = next(
        (it for it in items if it.get("sequencia") == sequencia),
        None,
    )
    assert target is not None, (
        f"item orfão sequencia={sequencia} não retornado"
    )
    assert target["actor_user_id"] is None
    assert target["actor_nome"] is None
    assert target["actor_user_email"] is None