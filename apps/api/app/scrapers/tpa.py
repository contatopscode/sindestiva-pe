"""SINDESTIVA-PE · Scraper TPA Tecnologia (SUAPE — http://tpa.ogmosuape.com.br).

Estrutura real do HTML (v1.24.0 do TPA Tecnologia, validada em 05/09/2026):
  - 2 tabelas `<table id="lousa">` (uma com classe `turno-diurno`, outra `turno-noturno`)
  - Cada tabela tem 14 linhas:
    - Row 0: SUAPE + nome dos turnos (rowspan 3)
    - Row 1: 4 grupos de funções (Funções de Mando, Terno, Funções Técnicas, Vigia)
    - Row 2: 26 funções individuais (C/M Geral, C/M Porão, ..., Rodízio, Contra Bordo)
    - Row 3+: 9-11 fainas (PRODUÇÃO, SALÁRIO, SACARIA SOLTA, ...) com células-ponteiro
  - Cada célula de faina tem 26+ colunas com texto = "ponteiro" (3 dígitos) ou "" (vazio)
  - Classes CSS: `funcoes` (cabeçalho), `fainas` (linha), `ponteiro` (valor), `ponteiro-vazio` (vazio)

Sprint 2 — refator T2-09 (05/09/2026):
  - Nomes do HTML (acentos, CSS line-break, abreviações tipo "Emp. GP")
    passam por `app.core.normalizadores.resolver_*_codigo` ANTES de virar
    `CelulaBruta`. O `CelulaBruta.faina_codigo` e `CelulaBruta.funcao_codigo`
    passam a carregar o `codigo` canônico do seed (`SACARIA`, `TECNICA_04`).
    Isso casa 1:1 com `lousa_main.fainas.codigo` e `lousa_main.funcoes.codigo`,
    destravando `lousa_alocacao` (que estava em 0 por causa do `catalogo_miss`).
  - **Dedup** por (faina, funcao) dentro de uma mesma tabela: o HTML agrega
    2 variantes visuais (ex: "SACARIA SOLTA" + "SACARIA PRÉ-LINGADA") em
    uma única faina canônica (`SACARIA`); o `CelulaBruta` final fica com
    1 entrada por célula, priorizando a **primeira** ocorrência (ordem do
    HTML = ordem que o TPA renderiza).
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
from app.core.normalizadores import (
    resolver_faina_codigo,
    resolver_funcao_codigo,
)
from app.scrapers.base import CelulaBruta, EscalaBruta, hash_conteudo

log = get_logger(__name__)


class _HttpGet(Protocol):
    async def get(self, url: str, **kwargs: Any) -> Any: ...


# URL real do TPA Tecnologia (validada em 05/09/2026)
TPA_URL_SUAPE = "http://tpa.ogmosuape.com.br/web/lousa_estiva"

# Mapeamento fixo das 26 funções (na ORDEM do HTML, validada em 05/09/2026).
# É MAIS CONFIÁVEL extrair do HTML, mas ter fallback evita "layout mudou"
# quando o TPA muda os nomes das funções.
FUNCOES_ORDEM = [
    "C/M GERAL",          # Mando 1
    "C/M PORÃO",          # Mando 2
    "C/M BLOCO",          # Mando 3
    "C/M RECHEGO",        # Mando 4
    "C/M CONSERTADOR",    # Mando 5
    "SUPERVISOR",         # Mando 6
    "PORÃO",              # Terno 1
    "BLOCO MAX",          # Terno 2
    "BLOCO",              # Terno 3
    "RECHEGO",            # Terno 4
    "CONSERTADOR",        # Terno 5
    "SHIP LOADER PORÃO",  # Terno 6
    "SINALEIRO",          # Técnica 1
    "GUINCHO A",          # Técnica 2
    "GUINCHO B",          # Técnica 3
    "EMPILHADOR GP",      # Técnica 4
    "EMPILHADOR PP",      # Técnica 5
    "VEÍCULO PESADO",     # Técnica 6
    "VEÍCULO LEVE",       # Técnica 7
    "MANOBRISTA",         # Técnica 8
    "TRANSPORTADOR",      # Técnica 9
    "PÁ MECÂNICA",        # Técnica 10
    "RETRO ESCAVADEIRA",  # Técnica 11
    "PC",                 # Técnica 12
    "RODÍZIO",            # Vigia 1
    "CONTRA BORDO",       # Vigia 2
]

FAINAS_ORDEM = [
    "PRODUÇÃO",
    "SALÁRIO",
    "SACARIA SOLTA",
    "SACARIA PRÉ-LINGADA",
    "RO-RO VEÍCULO LEVE",
    "RO-RO VEÍCULO LEVE ATÉ 400",
    "RO-RO VEÍCULO PESADO",
    "DIVERSOS E EQUIP. EÓLICOS",
    "CADASTRO",
    "SUPLEMENTAR",
    "TRABALHO EM ALTURA - NR 35",
]

# Mesma regex do scraper antigo (mantida como fallback se a estrutura mudar).
REGEX_CELULA = re.compile(
    r'data-faina="(?P<faina>[A-Z_0-9]+)"'
    r'.*?data-funcao="(?P<funcao>[A-Z_0-9]+)"'
    r'.*?data-matricula="(?P<matricula>[A-Z0-9\-]+)?"',
    re.IGNORECASE | re.DOTALL,
)


def _extrair_tabela_turno(table: BeautifulSoup, turno_classe: str) -> list[CelulaBruta]:
    """Extrai células de 1 tabela (DIURNO ou NOTURNO).

    Returns:
        Lista de `CelulaBruta` deduplicada por (faina_codigo, funcao_codigo).
        `faina_codigo` e `funcao_codigo` já são os **códigos canônicos**
        do seed (`lousa_main.funcoes.codigo` / `lousa_main.fainas.codigo`),
        após passar por `resolver_*_codigo()`. Células cujo nome não casa
        com nenhum catálogo são descartadas (log `catalogo_miss`).
        Cada `CelulaBruta.turno_codigo` é setado para o turno desta tabela
        (DIURNO ou NOTURNO) — fundamental para o `scraping_service`
        separar as células por turno (o TPA renderiza os 2 turnos na
        mesma página; sem este campo, teríamos UNIQUE violation em
        `lousa_alocacao.uq_alocacao_origem_faina_funcao`).
    """
    # Mapeia classe CSS do TPA → codigo do seed de turno
    TURNO_CLASSE_PARA_CODIGO = {
        "turno-diurno": "DIURNO",
        "turno-noturno": "NOTURNO",
    }
    turno_codigo = TURNO_CLASSE_PARA_CODIGO.get(turno_classe, "")

    # Verifica se a tabela é do turno certo (classe está em <td>, não no <table>)
    primeira_tr = table.find("tr")
    if not primeira_tr:
        return []
    html_interno = str(primeira_tr)
    if turno_classe not in html_interno:
        return []

    rows = table.find_all("tr")
    if len(rows) < 4:
        return []

    # Row 2 (índice 2) tem os nomes das 26 funções
    funcoes_row = rows[2]
    funcoes_tds = funcoes_row.find_all("td")
    # Pula o primeiro TD ("FAINAS" label) e o segundo (SUAPE se rowspan)
    funcoes_nomes = [td.get_text(strip=True).upper() for td in funcoes_tds]

    # Se as funções extraídas baterem com a nossa lista, usa elas;
    # senão cai pro mapeamento fixo (degradação graciosa).
    funcoes_validas = funcoes_nomes[2:] if len(funcoes_nomes) > 2 else funcoes_nomes[1:]
    if not funcoes_validas or len(funcoes_validas) < 20:
        funcoes_validas = FUNCOES_ORDEM

    # Dedup por (faina_codigo, funcao_codigo) — múltiplas variantes do HTML
    # (ex: "SACARIA SOLTA" e "SACARIA PRÉ-LINGADA") mapeiam para a mesma
    # chave canônica (`SACARIA`). Mantém a **primeira** ocorrência
    # (ordem do HTML = ordem que o fiscal vê na lousa).
    celulas_idx: dict[tuple[str, str], CelulaBruta] = {}

    # Rows 3+ são fainas
    for row in rows[3:]:
        # Detecta se é linha de faina (classe 'fainas' no primeiro TD)
        tds = row.find_all("td")
        if not tds:
            continue
        # O primeiro TD contém o nome da faina (com classe 'fainas' ou não)
        faina_nome_html = tds[0].get_text(strip=True).upper()
        if not faina_nome_html or faina_nome_html in ("FAINAS", ""):
            continue

        # Resolve faina HTML → codigo canônico do seed
        faina_codigo = resolver_faina_codigo(faina_nome_html)
        if faina_codigo is None:
            log.warning(
                "scraper_tpa.catalogo_miss_faina",
                turno=turno_classe,
                faina_html=faina_nome_html,
            )
            continue  # pula linha inteira

        # Os TDs seguintes (a partir do 2º) são os ponteiros
        # (o 1º TD é a faina, o 2º pode ser SUAPE, depois vêm as 26 funções)
        # Mas a estrutura exata depende do rowspan. Pegamos todos os TDs
        # e identificamos pelo conteúdo (3 dígitos = ponteiro).
        ponteiros_tds = [td for td in tds[1:] if "ponteiro" in (td.get("class") or [])]
        for i, td in enumerate(ponteiros_tds):
            texto = td.get_text(strip=True)
            # Pula células vazias
            if "ponteiro-vazio" in (td.get("class") or []):
                continue
            if not texto:
                continue

            # Mapear índice da célula de ponteiro → nome da função no HTML
            funcao_idx = i
            if funcao_idx >= len(funcoes_validas):
                funcao_nome_html = f"FUNCAO_{funcao_idx+1}"
            else:
                funcao_nome_html = funcoes_validas[funcao_idx]

            # Resolve função HTML → codigo canônico do seed
            funcao_codigo = resolver_funcao_codigo(funcao_nome_html)
            if funcao_codigo is None:
                log.warning(
                    "scraper_tpa.catalogo_miss_funcao",
                    turno=turno_classe,
                    faina=faina_codigo,
                    funcao_html=funcao_nome_html,
                )
                continue

            # Dedup: se já existe essa (faina, funcao), mantém a 1ª
            chave = (faina_codigo, funcao_codigo)
            if chave in celulas_idx:
                continue

            # Texto do ponteiro = "058" (3 dígitos) ou "012" etc
            matricula = texto.upper() if texto else None
            celulas_idx[chave] = CelulaBruta(
                faina_codigo=faina_codigo,
                funcao_codigo=funcao_codigo,
                trabalhador_matricula=matricula,
                turno_codigo=turno_codigo,
            )

    return list(celulas_idx.values())


def _parse_html(html: str) -> tuple[list[CelulaBruta], bool]:
    """Parser tolerante. Retorna (celulas, layout_mudou)."""
    soup = BeautifulSoup(html, "lxml")

    # Tenta extrair das 2 tabelas (DIURNO e NOTURNO)
    # As classes turno-diurno/noturno estão em <td> dentro da primeira <tr>
    # (não no <table> diretamente)
    celulas: list[CelulaBruta] = []
    for table in soup.find_all("table", id="lousa"):
        for turno_classe in ("turno-diurno", "turno-noturno"):
            celulas.extend(_extrair_tabela_turno(table, turno_classe))

    # Se não achou nada, tenta regex fallback (layout mudou)
    if not celulas:
        matches = REGEX_CELULA.findall(html)
        if matches:
            celulas_fallback: list[CelulaBruta] = []
            for m in matches:
                faina_html = m[0].upper()
                funcao_html = m[1].upper()
                matricula = m[2].upper() if m[2] else None
                faina_codigo = resolver_faina_codigo(faina_html)
                funcao_codigo = resolver_funcao_codigo(funcao_html)
                if faina_codigo is None or funcao_codigo is None:
                    log.warning(
                        "scraper_tpa.catalogo_miss_fallback",
                        faina_html=faina_html,
                        funcao_html=funcao_html,
                    )
                    continue
                celulas_fallback.append(
                    CelulaBruta(
                        faina_codigo=faina_codigo,
                        funcao_codigo=funcao_codigo,
                        trabalhador_matricula=matricula,
                    )
                )
            return celulas_fallback, True  # regex = layout mudou

    # Layout mudou se nenhuma célula extraída
    layout_mudou = len(celulas) == 0
    return celulas, layout_mudou


async def raspar_por_data(
    porto_slug: str,
    data: date,
    *,
    http_client: _HttpGet | None = None,
) -> EscalaBruta:
    """Raspa a lousa TPA Tecnologia para 1 (porto, data).

    Args:
        porto_slug: "SUAPE" (único porto coberto por TPA Tecnologia).
        data: data de referência (informativo, TPA sempre mostra hoje).
        http_client: cliente HTTP opcional (default cria um novo).

    Returns:
        EscalaBruta com HTML bruto, hash, células extraídas, duração.
    """
    if porto_slug.upper() != "SUAPE":
        return EscalaBruta(
            html_bruto="",
            content_hash=hash_conteudo(""),
            celulas=[],
            duracao_ms=0,
            url_origem=None,
            layout_mudou=False,
            erro_detalhes=f"TPA Tecnologia não cobre porto={porto_slug!r}.",
        )

    url = TPA_URL_SUAPE
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
        status_code = getattr(response, "status_code", 0)
        if status_code and status_code != 200:
            raise RuntimeError(f"TPA retornou status={status_code}")
    except Exception as exc:  # noqa: BLE001
        duracao = int((time.monotonic() - t0) * 1000)
        log.warning("scraper_tpa.http_error", url=url, erro=str(exc), duracao_ms=duracao)
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
    content_hash = hash_conteudo(html)

    log.info(
        "scraper_tpa.ok" if celulas else "scraper_tpa.sem_celulas",
        url=url,
        total=len(celulas),
        duracao_ms=duracao,
        layout_mudou=layout_mudou,
    )

    return EscalaBruta(
        html_bruto=html,
        content_hash=content_hash,
        celulas=celulas,
        duracao_ms=duracao,
        url_origem=url,
        layout_mudou=layout_mudou,
        erro_detalhes=None,
    )


# Entry point exportado pelo __init__.py
raspar_tpa = raspar_por_data
