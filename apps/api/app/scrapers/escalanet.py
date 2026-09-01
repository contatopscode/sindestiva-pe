"""SINDESTIVA-PE · Scraper EscalaNet (RECIFE — http://escalanet.recife.gov.br).

Sprint 2 T2-04: scraping tolerante (mesma filosofia do TPA — R2 do plano).

Estrutura do EscalaNet (padrão OGMO): HTML com `<table class="grade-escala">`
e linhas com `<tr data-linha="N" data-faina="..." data-funcao="...">`. A
documentação oficial do OGMO/PE descreve esta estrutura, mas a página
pode mudar.

Pipeline idêntico ao TPA Tecnologia: 3 níveis de seletor + regex fallback.
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
    async def get(self, url: str, **kwargs: Any) -> Any:
        ...


# ---------------------------------------------------------------------------
# Constantes do EscalaNet
# ---------------------------------------------------------------------------

ESCALANET_URL_TEMPLATE_RECIFE = (
    "http://escalanet.recife.gov.br/publico/escala?porto=recife&data={data}"
)

# EscalaNet tem uma estrutura mais simples (1 tabela por turno).
SELECTORES_TABELA = (
    "table.grade-escala tr",            # esperado (OGMO Recife)
    "table[id*='escala'] tr",           # genérico 1
    "table tbody tr",                   # genérico 2
)

# Regex fallback — EscalaNet costuma usar atributos data-* ou classes.
# Usa `re.DOTALL` pra casar através de newlines.
REGEX_CELULA = re.compile(
    r'class="linha"\s+'
    r'data-faina="(?P<faina>[A-Z_0-9]+)"\s+'
    r'data-funcao="(?P<funcao>[A-Z_0-9]+)"'
    r'.*?(?:data-matricula="(?P<matricula>[A-Z0-9\-]+)")?',
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
            # EscalaNet usa tanto data-* quanto classes CSS.
            faina = tr.get("data-faina") or ""
            funcao = tr.get("data-funcao") or ""
            matricula = tr.get("data-matricula")

            if not faina or not funcao:
                # Fallback: tentar extrair de classes (`.faina-X` / `.funcao-Y`).
                classes = tr.get("class", []) or []
                faina_match = next(
                    (c.replace("faina-", "") for c in classes if c.startswith("faina-")),
                    None,
                )
                funcao_match = next(
                    (c.replace("funcao-", "") for c in classes if c.startswith("funcao-")),
                    None,
                )
                faina = faina or (faina_match or "")
                funcao = funcao or (funcao_match or "")

            if not faina or not funcao:
                # Último recurso: texto da linha.
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
            return celulas, fallbacks_usados >= 3

    # Regex fallback.
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
        return celulas, True

    return [], True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def raspar_por_data(
    porto_slug: str,
    data: date,
    *,
    http_client: _HttpGet | None = None,
) -> EscalaBruta:
    """Raspa a lousa EscalaNet para 1 (porto, data).

    Args:
        porto_slug: "RECIFE" (único porto coberto pelo EscalaNet).
        data: data de referência da escala.
        http_client: cliente HTTP opcional (default cria um novo).

    Returns:
        EscalaBruta com HTML bruto, hash, células extraídas, duração.
    """
    if porto_slug.upper() != "RECIFE":
        return EscalaBruta(
            html_bruto="",
            content_hash=hash_conteudo(""),
            celulas=[],
            duracao_ms=0,
            url_origem=None,
            layout_mudou=False,
            erro_detalhes=f"EscalaNet não cobre porto={porto_slug!r}.",
        )

    url = ESCALANET_URL_TEMPLATE_RECIFE.format(data=data.isoformat())
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
        html = getattr(response, "text", "") or ""
    except Exception as exc:  # noqa: BLE001
        duracao = int((time.monotonic() - t0) * 1000)
        log.warning(
            "scraper_escalanet.http_error",
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
        "scraper_escalanet.ok",
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
