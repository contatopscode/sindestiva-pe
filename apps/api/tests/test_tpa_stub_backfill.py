"""SINDESTIVA-PE · Testes de backfill stub TPA (ALLOW_TPA_STUB)."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models import LousaAlocacao, Tpa
from app.services.tpa_stub_backfill_service import (
    backfill_stubs_from_lousa_alocacao,
    ensure_stub_tpa_for_matricula,
    synthetic_cpf_for_matricula,
)


def test_synthetic_cpf_deterministic() -> None:
    a = synthetic_cpf_for_matricula("058")
    b = synthetic_cpf_for_matricula("058")
    c = synthetic_cpf_for_matricula("059")
    assert a == b
    assert len(a) == 11
    assert a.isdigit()
    assert a != c


@pytest.mark.asyncio
async def test_stub_idempotent(db_session, monkeypatch) -> None:
    monkeypatch.setenv("ALLOW_TPA_STUB", "1")
    get_settings.cache_clear()

    tpa1, created1 = await ensure_stub_tpa_for_matricula(db_session, "300443")
    assert created1 is True
    tpa2, created2 = await ensure_stub_tpa_for_matricula(db_session, "300443")
    assert created2 is False
    assert tpa1.id == tpa2.id
    await db_session.commit()

    count = (
        await db_session.execute(
            select(Tpa).where(Tpa.matricula_ogmo == "300443")
        )
    ).scalars().all()
    assert len(count) == 1


@pytest.mark.asyncio
async def test_backfill_from_alocacao_links_trabalhador_id(
    db_session,
    monkeypatch,
) -> None:
    from app.models import Faina, Funcao, LousaEscalaOrigem, Porto, Turno
    from app.models.enums import FonteEscalaEnum, StatusScrapingEnum

    monkeypatch.setenv("ALLOW_TPA_STUB", "1")
    get_settings.cache_clear()

    porto = (await db_session.execute(select(Porto).where(Porto.codigo == "SUAPE"))).scalar_one()
    turno = (await db_session.execute(select(Turno).where(Turno.codigo == "DIURNO"))).scalar_one()
    faina = (await db_session.execute(select(Faina).limit(1))).scalar_one()
    funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()

    now = datetime.now(tz=timezone.utc)
    origem = LousaEscalaOrigem(
        fonte=FonteEscalaEnum.TPA,
        porto_id=porto.id,
        turno_id=turno.id,
        data_referencia=date.today(),
        url_origem="http://test",
        content_hash="a" * 64,
        payload_jsonb={},
        duracao_ms=1,
        status=StatusScrapingEnum.SUCESSO,
        scraped_at=now,
    )
    db_session.add(origem)
    await db_session.flush()

    aloc = LousaAlocacao(
        escala_origem_id=origem.id,
        porto_id=porto.id,
        turno_id=turno.id,
        faina_id=faina.id,
        funcao_id=funcao.id,
        data_referencia=date.today(),
        trabalhador_matricula="162",
        trabalhador_id=None,
        scraped_at=now,
    )
    db_session.add(aloc)
    await db_session.commit()

    result = await backfill_stubs_from_lousa_alocacao(db_session, days=7)
    assert result.get("created") == 1

    refreshed = (
        await db_session.execute(select(LousaAlocacao).where(LousaAlocacao.id == aloc.id))
    ).scalar_one()
    assert refreshed.trabalhador_id is not None

    tpa = (
        await db_session.execute(select(Tpa).where(Tpa.matricula_ogmo == "162"))
    ).scalar_one()
    assert refreshed.trabalhador_id == tpa.id
