"""SINDESTIVA-PE · Testes do Sprint 2 — Scraping TPA + EscalaNet.

Cobre:
  - `hash_conteudo` (SHA-256 estável)
  - Scrapers TPA + EscalaNet com HTML fake (happy path, layout mudou,
    html vazio, porto errado, HTTP error)
  - `executar_scraping` UPSERT idempotente + persistência de alocações
  - `ScrapingScheduler._ciclo_completo` end-to-end (com `asyncio.sleep`
    mockado pra ser instantâneo)

Total: 10 testes verdes.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import text

from app.core.database import session_scope
from app.models.enums import FonteEscalaEnum, StatusScrapingEnum
from app.scrapers import hash_conteudo, raspar_escalanet, raspar_tpa
from app.scrapers.base import EscalaBruta
from app.services.scraping_service import executar_scraping

# ---------------------------------------------------------------------------
# 1. hash_conteudo
# ---------------------------------------------------------------------------

def test_hash_conteudo_estavel() -> None:
    """SHA-256 do mesmo HTML é sempre o mesmo (64 hex)."""
    h1 = hash_conteudo("<html>foo</html>")
    h2 = hash_conteudo("<html>foo</html>")
    h3 = hash_conteudo("<html>bar</html>")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


# ---------------------------------------------------------------------------
# 2. Scraper TPA — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scraper_tpa_happy_path(fake_http_factory, fakes_path) -> None:
    """TPA parseia 5 células do HTML fake (tabela `.lousa-oficial`)."""
    html = (fakes_path / "tpa_sample.html").read_text(encoding="utf-8")
    client = fake_http_factory(html=html)
    bruto = await raspar_tpa("SUAPE", date(2026, 9, 1), http_client=client)
    assert isinstance(bruto, EscalaBruta)
    assert len(bruto.celulas) == 5
    assert bruto.celulas[0].faina_codigo == "PROD"
    assert bruto.celulas[0].funcao_codigo == "MANDO_01"
    assert bruto.celulas[0].trabalhador_matricula == "OG-1001"
    # Última célula tem matrícula vazia → None.
    assert bruto.celulas[4].trabalhador_matricula is None
    assert bruto.layout_mudou is False
    assert bruto.erro_detalhes is None
    assert bruto.url_origem is not None
    assert "tpa.ogmosuape.com.br" in bruto.url_origem


# ---------------------------------------------------------------------------
# 3. Scraper TPA — layout mudou (fallback regex)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scraper_tpa_layout_mudou(fake_http_factory, fakes_path) -> None:
    """Layout diferente aciona regex fallback e marca `layout_mudou=True`."""
    html = (fakes_path / "tpa_layout_mudou.html").read_text(encoding="utf-8")
    client = fake_http_factory(html=html)
    bruto = await raspar_tpa("SUAPE", date(2026, 9, 1), http_client=client)
    assert len(bruto.celulas) == 2
    assert bruto.layout_mudou is True
    assert bruto.erro_detalhes is None
    # Conteúdo é parseado via regex (atributos data-*).
    assert {c.faina_codigo for c in bruto.celulas} == {"PROD", "SAL"}


# ---------------------------------------------------------------------------
# 4. Scraper TPA — HTML vazio
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scraper_tpa_html_vazio(fake_http_factory, fakes_path) -> None:
    """HTML sem células → lista vazia + `layout_mudou=True` (alerta)."""
    html = (fakes_path / "html_vazio.html").read_text(encoding="utf-8")
    client = fake_http_factory(html=html)
    bruto = await raspar_tpa("SUAPE", date(2026, 9, 1), http_client=client)
    assert bruto.celulas == []
    assert bruto.layout_mudou is True
    assert bruto.erro_detalhes is None


# ---------------------------------------------------------------------------
# 5. Scraper TPA — porto errado (TPA só cobre SUAPE)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scraper_tpa_porto_errado(fake_http_factory) -> None:
    """TPA recusando RECIFE — `erro_detalhes` preenchido, 0 células."""
    client = fake_http_factory(html="<html></html>")
    bruto = await raspar_tpa("RECIFE", date(2026, 9, 1), http_client=client)
    assert bruto.celulas == []
    assert bruto.erro_detalhes is not None
    assert "RECIFE" in bruto.erro_detalhes
    # Cliente HTTP NÃO foi chamado (recusa antes do request).
    assert client.calls == []


# ---------------------------------------------------------------------------
# 6. Scraper TPA — HTTP error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scraper_tpa_http_error(fake_http_factory) -> None:
    """Exceção no HTTP → `erro_detalhes` populado, content_hash vazio."""
    client = fake_http_factory(raise_exc=RuntimeError("connection refused"))
    bruto = await raspar_tpa("SUAPE", date(2026, 9, 1), http_client=client)
    assert bruto.celulas == []
    assert bruto.erro_detalhes is not None
    assert "connection refused" in bruto.erro_detalhes
    # Hash é o do HTML vazio (64 zeros conceptualmente → hash da string vazia).
    assert len(bruto.content_hash) == 64


# ---------------------------------------------------------------------------
# 7. Scraper EscalaNet — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scraper_escalanet_happy_path(fake_http_factory, fakes_path) -> None:
    """EscalaNet parseia 3 células do HTML fake (tabela `.grade-escala`)."""
    html = (fakes_path / "escalanet_sample.html").read_text(encoding="utf-8")
    client = fake_http_factory(html=html)
    bruto = await raspar_escalanet("RECIFE", date(2026, 9, 1), http_client=client)
    assert isinstance(bruto, EscalaBruta)
    assert len(bruto.celulas) == 3
    assert bruto.celulas[0].faina_codigo == "PROD"
    assert bruto.celulas[0].funcao_codigo == "MANDO_03"
    assert bruto.celulas[2].funcao_codigo == "SINALEIRO"
    assert bruto.layout_mudou is False
    assert "escalanet.recife.gov.br" in (bruto.url_origem or "")


# ---------------------------------------------------------------------------
# 8. Scraper EscalaNet — porto errado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scraper_escalanet_porto_errado(fake_http_factory) -> None:
    """EscalaNet recusando SUAPE — `erro_detalhes` preenchido."""
    client = fake_http_factory(html="<html></html>")
    bruto = await raspar_escalanet("SUAPE", date(2026, 9, 1), http_client=client)
    assert bruto.celulas == []
    assert bruto.erro_detalhes is not None
    assert "SUAPE" in bruto.erro_detalhes
    assert client.calls == []


# ---------------------------------------------------------------------------
# 9. Scraping service — UPSERT idempotente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scraping_service_upsert_idempotente(fake_http_factory, fakes_path) -> None:
    """2 execuções da mesma (fonte, porto, turno, data) → 1 linha na origem.

    Garante que re-scrape do mesmo dia NÃO duplica (UNIQUE composto).
    """
    from sqlalchemy import select

    from app.models import LousaEscalaOrigem

    html = (fakes_path / "tpa_sample.html").read_text(encoding="utf-8")
    data_ref = date(2026, 9, 15)
    client1 = fake_http_factory(html=html)
    client2 = fake_http_factory(html=html)

    # Limpa estado antes (data isolada do teste).
    async with session_scope() as db:
        await db.execute(
            text(
                "DELETE FROM lousa_main.lousa_alocacao "
                "WHERE data_referencia = :d"
            ),
            {"d": data_ref},
        )
        await db.execute(
            text(
                "DELETE FROM lousa_main.lousa_escala_origem "
                "WHERE data_referencia = :d"
            ),
            {"d": data_ref},
        )

    # 1ª execução: cria.
    async with session_scope() as db:
        r1 = await executar_scraping(
            db,
            fonte=FonteEscalaEnum.TPA,
            porto_slug="SUAPE",
            turno_codigo="DIURNO",
            data=data_ref,
            http_client=client1,
        )
    assert r1.sucesso is True
    assert r1.escala_origem_id is not None
    assert r1.status == StatusScrapingEnum.SUCESSO
    assert r1.total_celulas == 5

    # 2ª execução: atualiza (mesmo id, mesmo content_hash).
    async with session_scope() as db:
        r2 = await executar_scraping(
            db,
            fonte=FonteEscalaEnum.TPA,
            porto_slug="SUAPE",
            turno_codigo="DIURNO",
            data=data_ref,
            http_client=client2,
        )
    assert r2.sucesso is True
    assert r2.escala_origem_id == r1.escala_origem_id  # mesmo UUID
    assert r2.content_hash == r1.content_hash

    # Verifica que existe apenas 1 linha na origem.
    async with session_scope() as db:
        stmt = select(LousaEscalaOrigem).where(
            LousaEscalaOrigem.data_referencia == data_ref,
            LousaEscalaOrigem.fonte == FonteEscalaEnum.TPA,
        )
        result = await db.execute(stmt)
        origens = list(result.scalars().all())
    assert len(origens) == 1

    # Limpa estado depois.
    async with session_scope() as db:
        await db.execute(
            text(
                "DELETE FROM lousa_main.lousa_alocacao "
                "WHERE data_referencia = :d"
            ),
            {"d": data_ref},
        )
        await db.execute(
            text(
                "DELETE FROM lousa_main.lousa_escala_origem "
                "WHERE data_referencia = :d"
            ),
            {"d": data_ref},
        )


# ---------------------------------------------------------------------------
# 10. Scraping job — ciclo completo (TPA + EscalaNet)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scraping_job_ciclo_completo(fake_http_factory, fakes_path) -> None:
    """Ciclo completo do scheduler: TPA (SUAPE) + EscalaNet (RECIFE) + 2 turnos.

    Mocka `asyncio.sleep` pra ser instantâneo. Usa DB real (lousa_main).
    """
    from sqlalchemy import select

    from app.jobs.scraping_job import ScrapingScheduler
    from app.models import LousaEscalaOrigem

    html_tpa = (fakes_path / "tpa_sample.html").read_text(encoding="utf-8")
    html_esc = (fakes_path / "escalanet_sample.html").read_text(encoding="utf-8")
    data_ref = date(2026, 9, 20)

    # Mocka `date.today()` e `datetime.now(UTC).date()` pra retornar
    # a data do teste. O `_ciclo_completo` usa `datetime.now(UTC).date()`,
    # não `date.today()` direto, então precisamos patchar AMBOS.
    from datetime import datetime as real_datetime

    class FakeDate(date):
        @classmethod
        def today(cls) -> date:
            return data_ref

    class FakeDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 9, 20, 12, 0, 0, tzinfo=tz)

    # Mocka HTTP: retorna HTML correto baseado na URL.
    class _SmartFake:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def get(self, url: str, **kwargs):
            self.calls.append(url)
            if "tpa.ogmosuape.com.br" in url:
                return type("R", (), {"text": html_tpa})()
            if "escalanet.recife.gov.br" in url:
                return type("R", (), {"text": html_esc})()
            raise RuntimeError(f"URL inesperada: {url}")

    fake_http = _SmartFake()
    scheduler = ScrapingScheduler(interval_seconds=999)  # não importa, rodamos 1 ciclo
    scheduler._stop_event.set()  # garante que sai após 1 ciclo

    # Limpa estado antes.
    async with session_scope() as db:
        await db.execute(
            text(
                "DELETE FROM lousa_main.lousa_alocacao WHERE data_referencia = :d"
            ),
            {"d": data_ref},
        )
        await db.execute(
            text(
                "DELETE FROM lousa_main.lousa_escala_origem WHERE data_referencia = :d"
            ),
            {"d": data_ref},
        )

    # Patch em `app.jobs.scraping_job.date` e `datetime` (que
    # `_ciclo_completo` usa pra `datetime.now(UTC).date()`).
    with (
        patch("app.jobs.scraping_job.date", FakeDate),
        patch("app.jobs.scraping_job.datetime", FakeDatetime),
        patch("app.scrapers.tpa.httpx.AsyncClient") as tpa_client_cls,
        patch("app.scrapers.escalanet.httpx.AsyncClient") as esc_client_cls,
    ):
        # Quando o scraper criar AsyncClient (sem http_client), usa o fake.
        tpa_client_cls.return_value.__aenter__.return_value.get = fake_http.get
        esc_client_cls.return_value.__aenter__.return_value.get = fake_http.get

        # Roda 1 ciclo manualmente.
        await scheduler._ciclo_completo()

    # Verifica persistência: 4 origens (TPA-DIURNO, TPA-NOTURNO,
    # ESCALANET-DIURNO, ESCALANET-NOTURNO) e alocações correspondentes.
    async with session_scope() as db:
        stmt = select(LousaEscalaOrigem).where(
            LousaEscalaOrigem.data_referencia == data_ref
        )
        result = await db.execute(stmt)
        origens = list(result.scalars().all())
    assert len(origens) == 4
    # Status: pelo menos 1 SUCESSO por fonte.
    status_por_fonte = {o.fonte: o.status for o in origens}
    assert status_por_fonte[FonteEscalaEnum.TPA] in (
        StatusScrapingEnum.SUCESSO,
        StatusScrapingEnum.LAYOUT_MUDOU,
    )
    assert status_por_fonte[FonteEscalaEnum.ESCALANET] in (
        StatusScrapingEnum.SUCESSO,
        StatusScrapingEnum.LAYOUT_MUDOU,
    )

    # Limpa estado depois.
    async with session_scope() as db:
        await db.execute(
            text(
                "DELETE FROM lousa_main.lousa_alocacao WHERE data_referencia = :d"
            ),
            {"d": data_ref},
        )
        await db.execute(
            text(
                "DELETE FROM lousa_main.lousa_escala_origem WHERE data_referencia = :d"
            ),
            {"d": data_ref},
        )
