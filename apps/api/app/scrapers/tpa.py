"""SINDESTIVA-PE · Scraper TPA Tecnologia (SUAPE — http://tpa.ogmosuape.com.br).

Sprint 2 T2-01: scraping tolerante (R2 do plano — TPA muda layout).

Pipeline:
  1. `httpx.AsyncClient` faz GET (timeout configurável).
  2. `BeautifulSoup(html, "lxml")` parseia.
  3. Parser tolerante 3 níveis:
     a) Seletor CSS específico (tabela `.lousa-table` ou similar)
     b) Seletor genérico (`table tr td[data-celula]`)
     c) Fallback regex no HTML bruto
     Se 3+ fallbacks acionam, marca `layout_mudou=True`.

Mock para testes: o parâmetro `http_client` aceita qualquer callable
async compatível com `httpx.AsyncClient.get`. Os testes em
`tests/test_scraping.py` usam um fake que retorna HTML estático.
"""
from __future__ import annotations

import re
import time
from datetime import date
from typing import Any, Protocol

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logging import get_logger
from app.scrapers.base import CelulaBruta, EscalaBruta, hash_conteudo

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Protocol de cliente HTTP (pra mock nos testes)
# ---------------------------------------------------------------------------

class _HttpGet(Protocol):
    """Subset de `httpx.AsyncClient.get` que o scraper usa."""

    async def get(self, url: str, **kwargs: Any) -> Any:
        ...


# ---------------------------------------------------------------------------
# Constantes do TPA Tecnologia (URL template + seletores tolerantes)
# ---------------------------------------------------------------------------

# URL do TPA Tecnologia para SUAPE (vem de `portos.url_tpa` no seed).
# Default aqui cobre o caso de o scraper ser chamado sem contexto.
TPA_URL_TEMPLATE_SUAPE = "http://tpa.ogmosuape.com.br/escala?data={data}"

# Seletores tentados em ordem (1º é o esperado, 2º-3º são fallbacks).
SELECTORES_TABELA = (
    "table.lousa-oficial tr",       # esperado (v1.0 TPA)
    "table tr[class*='celula']",    # genérico 1
    "table tr",                     # genérico 2
)

# Regex fallback — procura padrão "faina|funcao|matricula" no HTML.
# Captura: faina, funcao, matricula (alfanumérico + hífen pra OG-XXXX).
# Usa `re.DOTALL` pra casar através de newlines (atributos data-* podem
# estar quebrados em múltiplas linhas no HTML real). `.*?` (non-greedy)
# garante que pegamos só a próxima tupla.
REGEX_CELULA = re.compile(
    r'data-faina="(?P<faina>[A-Z_0-9]+)"'
    r'.*?data-funcao="(?P<funcao>[A-Z_0-9]+)"'
    r'.*?data-matricula="(?P<matricula>[A-Z0-9\-]+)?"',
    re.IGNORECASE | re.DOTALL,
)


# ---------------------------------------------------------------------------
# Parser tolerante
# ---------------------------------------------------------------------------

def _parse_html(html: str) -> tuple[list[CelulaBruta], bool]:
    """Parser tolerante 3 níveis. Retorna (celulas, layout_mudou)."""
    soup = BeautifulSoup(html, "lxml")
    fallbacks_usados = 0

    for nivel, seletor in enumerate(SELECTORES_TABELA, start=1):
        try:
            rows = soup.select(seletor)
        except Exception:  # noqa: BLE001
            rows = []

        if not rows:
            fallbacks_usados += 1
            continue

        celulas: list[CelulaBruta] = []
        for tr in rows:
            faina = tr.get("data-faina") or ""
            funcao = tr.get("data-funcao") or ""
            matricula = tr.get("data-matricula")
            # Fallback: pegar do texto da linha se attrs vazios.
            if not faina or not funcao:
                texto = tr.get_text(" ", strip=True)
                partes = texto.split()
                if len(partes) >= 2:
                    faina = faina or partes[0]
                    funcao = funcao or partes[1]
                    matricula = matricula or (partes[2] if len(partes) > 2 else None)
            if faina and funcao:
                celulas.append(CelulaBruta(
                    faina_codigo=str(faina).upper(),
                    funcao_codigo=str(funcao).upper(),
                    trabalhador_matricula=str(matricula).upper() if matricula else None,
                ))

        if celulas:
            # `layout_mudou` = 3 fallbacks acionados (R2 do plano).
            return celulas, fallbacks_usados >= 3

    # Último fallback: regex no HTML bruto.
    matches = REGEX_CELULA.findall(html)
    if matches:
        celulas = [
            CelulaBruta(
                faina_codigo=m[0].upper(),
                funcao_codigo=m[1].upper(),
                trabalhador_matricula=m[2].upper() if m[2] else None,
            )
            for m in matches
        ]
        return celulas, True  # regex = layout mudou

    return [], True  # sem dados = layout mudou (alerta)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def raspar_por_data(
    porto_slug: str,
    data: date,
    *,
    http_client: _HttpGet | None = None,
) -> EscalaBruta:
    """Raspa a lousa TPA Tecnologia para 1 (porto, data).

    Args:
        porto_slug: "SUAPE" (único porto coberto por TPA Tecnologia).
        data: data de referência da escala.
        http_client: cliente HTTP opcional (default cria um novo). Útil
            para testes — passa um fake que retorna HTML estático.

    Returns:
        EscalaBruta com HTML bruto, hash, células extraídas, duração.
    """
    if porto_slug.upper() != "SUAPE":
        # TPA Tecnologia cobre só SUAPE. Para RECIFE, use o EscalaNet.
        return EscalaBruta(
            html_bruto="",
            content_hash=hash_conteudo(""),
            celulas=[],
            duracao_ms=0,
            url_origem=None,
            layout_mudou=False,
            erro_detalhes=f"TPA Tecnologia não cobre porto={porto_slug!r}.",
        )

    url = TPA_URL_TEMPLATE_SUAPE.format(data=data.isoformat())
    t0 = time.monotonic()
    try:
        if http_client is None:
            async with httpx.AsyncClient(
                timeout=settings.scraper_timeout,
                headers={"User-Agent": settings.scraper_user_agent},
            ) as client:
                response = await client.get(url)
        else:
            response = await http_client.get(url)

        # Em prod, TPA pode retornar 503 ou redirect. Aqui só aceitamos 200.
        html = getattr(response, "text", "") or ""
    except Exception as exc:  # noqa: BLE001
        duracao = int((time.monotonic() - t0) * 1000)
        log.warning(
            "scraper_tpa.http_error",
            url=url,
            erro=str(exc),
            duracao_ms=duracao,
        )
        return EscalaBruta(
            html_bruto="",
            content_hash=hash_conteudo(""),
            celulas=[],
            duracao_ms=duracao,
            url_origem=url,
            layout_mudou=False,
            erro_detalhes=f"HTTP error: {exc!s}",
        )

    duracao = int((time.monotonic() - t0) * 1000)
    celulas, layout_mudou = _parse_html(html)
    log.info(
        "scraper_tpa.ok",
        url=url,
        celulas=len(celulas),
        duracao_ms=duracao,
        layout_mudou=layout_mudou,
    )
    return EscalaBruta(
        html_bruto=html,
        content_hash=hash_conteudo(html),
        celulas=celulas,
        duracao_ms=duracao,
        url_origem=url,
        layout_mudou=layout_mudou,
    )


__all__ = ["raspar_por_data"]
