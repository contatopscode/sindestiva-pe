"""SINDESTIVA-PE · Testes de invariantes dos models (Sprint 1).

Cobre invariantes de schema e constraints do banco:
  - email citext (case-insensitive)
  - purge_after default (User 24m, Fiscal 5a — D2)
  - constraint ck_users_password_for_non_tpa (TPA sem senha)
  - trigger fn_remanejamentos_codigo_se (formato SE-YYYYMMDD-NNN)
  - trigger tg_audit_block_update (audit_events imutável)

Total: 6 testes verdes.

Observação sobre `ck_users_password_for_non_tpa`: a constraint só
aplica a users com role='TPA'. Pra testar, inserimos direto via SQL
(ignorando o ORM, que validaria antes).
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.core.security import hash_password
from app.models import (
    Fiscal,
    LousaSnapshot,
    Remanejamento,
    RoleEnum,
    StatusRemanejamentoEnum,
    Tpa,
    User,
    UserStatusEnum,
)
from app.models.enums import TpaStatusEnum


# ---------------------------------------------------------------------------
# 1. Email citext
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_cpf_citext_e_case_insensitive(db_session) -> None:
    """Emails com casing diferente batem no mesmo User (citext).

    Postgres CITEXT é case-insensitive nativamente. A coluna `email`
    é citext → "PAULO@..." e "paulo@..." retornam o mesmo user.
    """
    import secrets as _sec  # noqa: PLC0415

    email = f"mixedcase-{_sec.token_hex(4)}@test.com"
    u = User(
        email=email,
        password_hash=hash_password("x"),
        role=RoleEnum.FISCAL,
        status=UserStatusEnum.ATIVO,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)

    # SELECT com lowercase retorna o mesmo user.
    stmt = select(User).where(User.email == email.lower())
    found = (await db_session.execute(stmt)).scalar_one()
    assert found.id == u.id

    # E com uppercase também.
    stmt = select(User).where(User.email == email.upper())
    found2 = (await db_session.execute(stmt)).scalar_one()
    assert found2.id == u.id


# ---------------------------------------------------------------------------
# 2. purge_after default (User 24m)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_purge_after_default_24m(db_session) -> None:
    """User novo tem `purge_after` ~ 24 meses no futuro (default SoftDeleteMixin)."""
    import secrets as _sec  # noqa: PLC0415

    before = datetime.now(tz=timezone.utc)
    u = User(
        email=f"purge-test-{_sec.token_hex(4)}@x.com",
        password_hash=hash_password("x"),
        role=RoleEnum.FISCAL,
        status=UserStatusEnum.ATIVO,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)

    assert u.purge_after is not None
    expected = before + timedelta(days=24 * 30)  # ~24 meses (30 dias/mês)
    delta = abs((u.purge_after - expected).total_seconds())
    # Tolera ±31 dias (24m = 720 dias, range amplo).
    assert delta < 31 * 24 * 3600, f"purge_after fora de 24m: delta={delta}s"


# ---------------------------------------------------------------------------
# 3. Fiscal purge_after 5 anos (D2)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fiscal_purge_after_5_anos(db_session) -> None:
    """Fiscal tem `purge_after` ~ 5 anos no futuro (D2 — audit fiscal).

    Model `perfis_internos.py` sobrescreve `purge_after` com
    `server_default=now() + INTERVAL '5 years'`.
    """
    import secrets as _sec  # noqa: PLC0415

    from app.models import Funcao, Porto, Turno  # noqa: PLC0415

    # User necessário pra FK em Fiscal.
    u = User(
        email=f"fiscal-5a-{_sec.token_hex(4)}@test.com",
        password_hash=hash_password("x"),
        role=RoleEnum.FISCAL,
        status=UserStatusEnum.ATIVO,
    )
    db_session.add(u)
    await db_session.flush()
    porto = (await db_session.execute(select(Porto).limit(1))).scalar_one()
    turno = (await db_session.execute(select(Turno).limit(1))).scalar_one()
    funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()

    before = datetime.now(tz=timezone.utc)
    f = Fiscal(
        user_id=u.id,
        cpf=f"{secrets.randbelow(10**10):010d}1",  # 11 dígitos únicos
        nome_completo="Fiscal 5 Anos",
        matricula_sindicato=f"FISC-T-{secrets.token_hex(2).upper()}"[:10],
        telefone="+5581999998888",
        porto_id=porto.id,
        turno_id=turno.id,
        data_inicio=before.date(),
    )
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)

    expected = before + timedelta(days=5 * 365)
    delta = abs((f.purge_after - expected).total_seconds())
    # Tolera ±31 dias (5a = 1825 dias).
    assert delta < 31 * 24 * 3600, f"fiscal.purge_after fora de 5a: delta={delta}s"


# ---------------------------------------------------------------------------
# 4. Constraint ck_users_password_for_non_tpa
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tpa_sem_password_hash_via_constraint(db_session) -> None:
    """User TPA com password_hash NOT NULL viola `ck_users_password_for_non_tpa`.

    O ORM aceita o `password_hash` (sem validação de modelo), mas o
    CHECK constraint no Postgres rejeita. Testamos a constraint
    diretamente via INSERT cru.
    """
    # Cria user TPA com password_hash via SQL direto (bypass do ORM).
    with pytest.raises(Exception) as exc:
        await db_session.execute(
            text(
                """
                INSERT INTO lousa_main.users
                (email, telefone, password_hash, role, status)
                VALUES (:email, :tel, :pwd, 'TPA', 'ATIVO')
                """
            ),
            {
                "email": "tpa-com-senha@test.com",
                "tel": "+5581999997777",
                "pwd": hash_password("deveria-falhar"),
            },
        )
        await db_session.commit()
    assert "ck_users_password_for_non_tpa" in str(exc.value)


# ---------------------------------------------------------------------------
# 5. Trigger fn_remanejamentos_codigo_se
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_remanejamento_codigo_se_formato(
    db_session, seed_users
) -> None:
    """INSERT em `remanejamentos` com `codigo_se` vazio → trigger gera
    `SE-YYYYMMDD-NNN` (3 dígitos)."""
    from app.models import Faina, Funcao, Porto, Turno  # noqa: PLC0415
    from app.models.enums import TpaStatusEnum  # noqa: PLC0415

    # Recupera dados auxiliares (não cleanup'd).
    porto = (await db_session.execute(select(Porto).limit(1))).scalar_one()
    turno = (await db_session.execute(select(Turno).limit(1))).scalar_one()
    funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()
    faina = (await db_session.execute(select(Faina).limit(1))).scalar_one()

    # Cria Tpa (FK em remanejamentos.tpa_in_id e tpa_out_id).
    tpa_email = f"tpa-rem-test-{secrets.token_hex(4)}@test.com"
    u = User(
        email=tpa_email,
        password_hash=hash_password("x"),
        role=RoleEnum.FISCAL,
        status=UserStatusEnum.ATIVO,
    )
    db_session.add(u)
    await db_session.flush()
    tpa = Tpa(
        user_id=u.id,
        cpf=f"{secrets.randbelow(10**10):010d}2",
        nome_completo="TPA Rem Test",
        matricula_ogmo=f"OG-{secrets.token_hex(2).upper()}"[:10],  # <= 10 chars
        telefone="+5581999996666",
        funcao_base_id=funcao.id,
        categoria="Mando",
        status_cadastro=TpaStatusEnum.ATIVO,
    )
    db_session.add(tpa)
    await db_session.flush()

    # Cria LousaSnapshot via raw SQL (model tem muitos campos).
    snapshot_id = (
        await db_session.execute(
            text("SELECT gen_random_uuid()")
        )
    ).scalar()
    await db_session.execute(
        text(
            """
            INSERT INTO lousa_main.lousa_snapshots
            (id, porto_id, turno_id, fonte, html_hash_sha256, total_celulas,
             total_tpas_escalados, duracao_scrape_ms, status, scraped_at)
            VALUES (:id, :porto, :turno, 'MANUAL_TEST', :h, 0, 0, 0, 'OK', now())
            """
        ),
        {"id": snapshot_id, "porto": porto.id, "turno": turno.id, "h": secrets.token_hex(32)},
    )

    # fiscal_id: Manoel é FISCAL, usamos ele (preservado pelo cleanup).
    fiscal_id = (
        await db_session.execute(
            text(
                """
                SELECT f.id FROM lousa_main.fiscais f
                JOIN lousa_main.users u ON u.id = f.user_id
                WHERE u.email = 'manoel@sindestiva-pe.com.br'
                """
            )
        )
    ).scalar_one()

    # Cria Remanejamento com codigo_se vazio → trigger deve preencher.
    rem_id = (await db_session.execute(text("SELECT gen_random_uuid()"))).scalar()
    unique_hash = secrets.token_hex(32)
    await db_session.execute(
        text(
            """
            INSERT INTO lousa_main.remanejamentos
            (id, codigo_se, snapshot_origem_id, porto_id, turno_id, tpa_out_id,
             tpa_in_id, funcao_origem_id, faina_origem_id, data_referencia,
             motivo, motivo_outro_texto, fiscal_id, base_legal_texto_livre,
             status, hash_evento)
            VALUES (:id, '', :snap, :porto, :turno, :tpa_out, :tpa_in, :func, :faina,
                    :data, 'OUTRO', 'Test motivo (Sprint 1)', :fiscal,
                    'Test base legal (Sprint 1)', 'PENDENTE', :h)
            RETURNING codigo_se
            """
        ),
        {
            "id": rem_id,
            "snap": snapshot_id,
            "porto": porto.id,
            "turno": turno.id,
            "tpa_out": tpa.id,
            "tpa_in": tpa.id,
            "func": funcao.id,
            "faina": faina.id,
            "data": datetime.now(tz=timezone.utc).date(),
            "fiscal": fiscal_id,  # nome da chave TEM que ser "fiscal" (não "fiscal_id")
            "h": unique_hash,
        },
    )
    await db_session.commit()

    # Re-busca codigo_se.
    codigo_se = (
        await db_session.execute(
            text("SELECT codigo_se FROM lousa_main.remanejamentos WHERE id = :id"),
            {"id": rem_id},
        )
    ).scalar()

    # Trigger preencheu codigo_se no formato SE-YYYYMMDD-NNN.
    assert codigo_se is not None
    assert codigo_se != ""
    pattern = r"^SE-\d{8}-\d{3}$"
    assert re.match(pattern, codigo_se), f"codigo_se fora do formato: {codigo_se!r}"


# ---------------------------------------------------------------------------
# 6. Trigger tg_audit_block_update (audit_events imutável)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_events_imutavel_via_trigger(db_session) -> None:
    """UPDATE em `audit_events` levanta exception (trigger `tg_audit_block_update`).

    Inserimos 1 row via raw SQL com hash único, depois tentamos UPDATE.
    """
    unique_hash = secrets.token_hex(32)  # 64 chars hex
    # INSERT raw de 1 evento de auditoria.
    await db_session.execute(
        text(
            """
            INSERT INTO lousa_main.audit_events
            (sequencia, entity_type, entity_id, event_type, hash_evento,
             hash_anterior, payload_before, payload_after, criado_em)
            VALUES (
                (SELECT COALESCE(MAX(sequencia), 0) + 1 FROM lousa_main.audit_events),
                'test', gen_random_uuid(), 'TEST_EVENT',
                :h, '', '{}'::jsonb, '{}'::jsonb, now()
            )
            """
        ),
        {"h": unique_hash},
    )
    await db_session.commit()

    # UPDATE deve falhar com TABELA_IMUTAVEL.
    with pytest.raises(Exception) as exc:
        await db_session.execute(
            text("UPDATE lousa_main.audit_events SET event_type = 'HACKED'"),
        )
        await db_session.commit()
    assert "TABELA_IMUTAVEL" in str(exc.value)
