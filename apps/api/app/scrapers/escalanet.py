"""SINDESTIVA-PE · Scraper EscalaNet (RECIFE — OGMO Recife).

Sprint 2 T2-04: scraping tolerante (mesma filosofia do TPA — R2 do plano).

ATENÇÃO (07/09/2026): URL original era `escalanet.recife.gov.br` mas o
domínio **não resolve DNS** — foi descontinuado. URL real descoberta:

    https://www.ogmo-recife.org.br/EscalaNet/

Estrutura HTML retornada por `RelatorioResultadoEscala.php`:

    <table class="relatorio">
      <tr><td colspan=5><center><h2>Resultado da Escalação - Estiva</h2>
        <b>Data:</b> 07/09/2026
        <b>Período:</b> 0800/1400</center><br></td></tr>
      <tr class="titulo"><td colspan=5>
        <table width=100%><tr>
          <td width=250px>CAIS 02</td>
          <td align=center>Navio: WL MUROM</td>
          <td width=250px align=right>Operador: SUAPE</td>
        </tr></table></td></tr>
      <tr class="subtitulo"><td colspan=5 align=center>Terno 1</td></tr>
      <tr class="legenda"><td>Função</td><td>TPA</td><td>Nº Ogmo</td><td>Ord</td><td>Escala Extra</td></tr>
      <tr><td>CONTRAMESTRE GERAL</td><td>MARCONE PEDRO DE SOUZA</td><td>300443</td><td>183</td><td>N</td></tr>
      ...

Períodos disponíveis (categoria=01, ESTIVA):
  46 → 0800/1400 (manhã)
  47 → 1400/2000 (tarde)
  48 → 2000/0200 (noite 1)
  49 → 0200/0800 (madrugada)

Pipeline: 3 níveis de seletor + regex fallback.
"""

from __future__ import annotations

import re
import time
from datetime import date
from typing import Any, Protocol

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.scrapers.base import CelulaBruta, EscalaBruta, hash_conteudo

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Protocol de cliente HTTP (pra mock nos testes)
# ---------------------------------------------------------------------------


class _HttpGet(Protocol):
    async def get(self, url: str, **kwargs: Any) -> Any: ...

    async def post(self, url: str, **kwargs: Any) -> Any: ...


# ---------------------------------------------------------------------------
# Constantes do EscalaNet (URL REAL — descoberta 07/09/2026)
# ---------------------------------------------------------------------------

ESCALANET_BASE_URL = "http://www.ogmo-recife.org.br/EscalaNet"

# Endpoint AJAX que retorna o relatório (não a página inicial).
ESCALANET_RELATORIO_URL = f"{ESCALANET_BASE_URL}/RelatorioResultadoEscala.php"

# Página de formulário (não é raspada — só pra `Referer`).
ESCALANET_FORM_URL = f"{ESCALANET_BASE_URL}/Index.php?acao=ResultadoEscala&cat=estiva"

# Categoria: 01 = ESTIVA (única usada pelo OGMO Recife).
ESCALANET_CATEGORIA = "01"

# Períodos do EscalaNet → turno do nosso sistema (DIURNO/NOTURNO).
# 46 (0800/1400) + 47 (1400/2000) → DIURNO
# 48 (2000/0200) + 49 (0200/0800) → NOTURNO
ESCALANET_PERIODOS: tuple[tuple[str, str, str], ...] = (
    ("46", "DIURNO", "0800/1400"),
    ("47", "DIURNO", "1400/2000"),
    ("48", "NOTURNO", "2000/0200"),
    ("49", "NOTURNO", "0200/0800"),
)

# Mapeamento: nome da função em PT-BR (EscalaNet) → código do nosso catálogo.
# Fainas em Recife: PRODUCAO (capatazia de cais principal).
ESCALANET_FUNCAO_PARA_CODIGO: dict[str, tuple[str, str]] = {
    # (funcao_codigo, faina_codigo) — default faina = PRODUCAO
    "CONTRAMESTRE GERAL": ("MANDO_01", "PRODUCAO"),
    "CONTRAMESTRE DE PORÃO": ("MANDO_02", "PRODUCAO"),
    "CONTRAMESTRE DE BLOCO": ("MANDO_03", "PRODUCAO"),
    "CONTRAMESTRE DE RECHEGO": ("MANDO_04", "PRODUCAO"),
    "CONTRAMESTRE DE CONTAINER": ("MANDO_05", "PRODUCAO"),
    "SUPERVISOR": ("MANDO_06", "PRODUCAO"),
    "TRABALHADOR DE PORÃO": ("TERNO_01", "PRODUCAO"),
    "TRABALHADOR DE BLOCO MAX": ("TERNO_02", "PRODUCAO"),
    "TRABALHADOR DE BLOCO": ("TERNO_03", "PRODUCAO"),
    "TRABALHADOR DE RECHEGO": ("TERNO_04", "PRODUCAO"),
    "TRABALHADOR DE CONTAINER": ("TERNO_05", "PRODUCAO"),
    "SHIP LOADER": ("TERNO_06", "PRODUCAO"),
    "SINALEIRO": ("TECNICA_01", "PRODUCAO"),
    "OPERADOR DE GUINCHO TIPO A": ("TECNICA_02", "PRODUCAO"),
    "OPERADOR DE GUINCHO TIPO B": ("TECNICA_03", "PRODUCAO"),
    "OPERADOR DE EMPILHADEIRA GP": ("TECNICA_04", "PRODUCAO"),
    "OPERADOR DE EMPILHADEIRA PP": ("TECNICA_05", "PRODUCAO"),
    "OPERADOR DE VEÍCULO PESADO": ("TECNICA_06", "PRODUCAO"),
    "OPERADOR DE VEÍCULO LEVE": ("TECNICA_07", "PRODUCAO"),
    "MANOBRISTA": ("TECNICA_08", "PRODUCAO"),
    "TRANSPORTE": ("TECNICA_09", "PRODUCAO"),
    "PÁ CARREGADEIRA": ("TECNICA_10", "PRODUCAO"),
    "VIGIA PORTO": ("VIGIA_01", "PRODUCAO"),
    "VIGIA CAIS": ("VIGIA_02", "PRODUCAO"),
}

# Regex que captura uma linha de TPA: <td>FUNÇÃO</td><td>NOME</td><td>MATRICULA</td><td>ORD</td><td>EXTRA</td>
# Tolera espaços/quebras e atributos extras.
REGEX_TPA_ROW = re.compile(
    r"<td[^>]*>\s*(?P<funcao>[^<]{3,80}?)\s*</td>\s*"
    r"<td[^>]*>\s*(?P<nome>[^<]{3,80}?)\s*</td>\s*"
    r"<td[^>]*>\s*(?P<matricula>\d{4,8})\s*</td>\s*"
    r"<td[^>]*>\s*(?P<ord>\d+)\s*</td>\s*"
    r"<td[^>]*>\s*(?P<extra>[NS])\s*</td>",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers de parsing
# ---------------------------------------------------------------------------


def _normalizar_funcao(texto: str) -> tuple[str, str]:
    """Mapeia nome PT-BR do EscalaNet → (funcao_codigo, faina_codigo).

    Fallback: mantém o texto original em maiúsculas como funcao_codigo e
    assume PRODUCAO como faina. Sinaliza com sufixo '_RAW' pro chamador
    saber que precisa cadastrar a função.
    """
    txt = texto.strip().upper()
    # Tira acentos (rápido).
    sem_acento = (
        txt.replace("Ç", "C")
        .replace("Ã", "A")
        .replace("Õ", "O")
        .replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
        .replace("Â", "A")
        .replace("Ê", "E")
    )
    if sem_acento in ESCALANET_FUNCAO_PARA_CODIGO:
        return ESCALANET_FUNCAO_PARA_CODIGO[sem_acento]
    # Tenta match parcial (alguns nomes têm sufixos tipo "TIPO A" / "TIPO B").
    for chave, valor in ESCALANET_FUNCAO_PARA_CODIGO.items():
        if chave in sem_acento or sem_acento in chave:
            return valor
    return (f"FUNCAO_RAW_{sem_acento[:20].replace(' ', '_')}", "PRODUCAO")


def _parse_html(html: str) -> list[CelulaBruta]:
    """Extrai (faina, função, matrícula) de cada linha de TPA no HTML.

    Agrega múltiplas matrículas para a mesma (faina, função) em uma
    única `CelulaBruta` com matriculas separadas por vírgula. Necessário
    porque `lousa_alocacao` tem UNIQUE `(escala_origem_id, faina_id,
    funcao_id)` (Sprint 2 T2-08) — 1 célula por (origem, faina, função).
    A lousa real tem múltiplos TPAs na mesma função (ex: 6 trabalhadores
    de porão num mesmo terno).
    """
    matches = REGEX_TPA_ROW.findall(html)
    agregado: dict[tuple[str, str], list[str]] = {}
    for funcao_nome, _nome, matricula, _ord, _extra in matches:
        funcao_codigo, faina_codigo = _normalizar_funcao(funcao_nome)
        chave = (faina_codigo, funcao_codigo)
        agregado.setdefault(chave, []).append(matricula.strip())

    celulas: list[CelulaBruta] = []
    for (faina_codigo, funcao_codigo), matriculas in agregado.items():
        # Junta matriculas, dedup, ordena. Mantém ordem de inserção.
        seen: set[str] = set()
        uniq: list[str] = []
        for m in matriculas:
            if m not in seen:
                seen.add(m)
                uniq.append(m)
        celulas.append(
            CelulaBruta(
                faina_codigo=faina_codigo,
                funcao_codigo=funcao_codigo,
                trabalhador_matricula=",".join(uniq),
                turno_codigo="",  # turno vem do periodo no caller
            )
        )
    return celulas


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def _raspar_periodo(
    data: date,
    periodo_codigo: str,
    turno_codigo: str,
    *,
    http_client: _HttpGet | None = None,
) -> tuple[list[CelulaBruta], bool]:
    """Raspa 1 período. Retorna (celulas, layout_mudou).

    layout_mudou=True só quando a resposta HTTP **não tem a estrutura
    esperada** (HTML mudou, OGMO tirou do ar, etc.). Quando o turno
    simplesmente ainda não foi processado pelo OGMO (sem TPAs escalados
    no horário), retorna (celulas=[], layout_mudou=False).
    """
    form_data = {
        "categoria": ESCALANET_CATEGORIA,
        "data": data.strftime("%d/%m/%Y"),
        "periodo": periodo_codigo,
        "navio": "",
        "funcao": "",
    }
    headers = {
        "Referer": ESCALANET_FORM_URL,
        "User-Agent": settings.scraper_user_agent,
    }
    t0 = time.monotonic()
    try:
        if http_client is None:
            async with httpx.AsyncClient(timeout=settings.scraper_timeout) as client:
                response = await client.post(
                    ESCALANET_RELATORIO_URL,
                    data=form_data,
                    headers=headers,
                )
        else:
            response = await http_client.post(
                ESCALANET_RELATORIO_URL,
                data=form_data,
                headers=headers,
            )
        html = getattr(response, "text", "") or ""
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "scraper_escalanet.http_error",
            periodo=periodo_codigo,
            erro=str(exc),
        )
        return [], True  # erro de rede = sinal de layout mudou

    duracao = int((time.monotonic() - t0) * 1000)

    # Marcador de "resposta OK": página de relatório tem o título fixo.
    layout_ok = "Resultado da Escalação" in html
    if not layout_ok:
        log.warning(
            "scraper_escalanet.layout_mudou",
            periodo=periodo_codigo,
            html_size=len(html),
        )
        return [], True

    celulas_brutas = _parse_html(html)
    # CelulaBruta é frozen + slots → recria com turno_codigo setado.
    celulas = [
        CelulaBruta(
            faina_codigo=c.faina_codigo,
            funcao_codigo=c.funcao_codigo,
            trabalhador_matricula=c.trabalhador_matricula,
            turno_codigo=turno_codigo,
        )
        for c in celulas_brutas
    ]
    log.info(
        "scraper_escalanet.ok",
        periodo=periodo_codigo,
        turno=turno_codigo,
        celulas=len(celulas),
        duracao_ms=duracao,
    )
    return celulas, False


async def raspar_por_data(
    porto_slug: str,
    data: date,
    *,
    http_client: _HttpGet | None = None,
) -> EscalaBruta:
    """Raspa a lousa EscalaNet para 1 (porto, data).

    Para cada um dos 4 períodos (46/47/48/49), faz POST e agrega.
    Atribui turno_codigo (DIURNO/NOTURNO) baseado no período.

    Args:
        porto_slug: "RECIFE" (único porto coberto pelo EscalaNet).
        data: data de referência da escala.

    Returns:
        EscalaBruta com HTML bruto concatenado, hash agregado, células
        com turno_codigo setado.
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

    t0 = time.monotonic()
    html_bruto_total = ""
    celulas_total: list[CelulaBruta] = []
    layout_mudou = False

    for periodo_codigo, turno_codigo, _rotulo in ESCALANET_PERIODOS:
        celulas_p, layout_mudou_p = await _raspar_periodo(
            data,
            periodo_codigo,
            turno_codigo,
            http_client=http_client,
        )
        celulas_total.extend(celulas_p)
        # layout_mudou só é True se a estrutura HTML em si mudou.
        # Período sem TPAs (turno ainda não começou) = layout OK, sem dados.
        if layout_mudou_p:
            layout_mudou = True

    duracao = int((time.monotonic() - t0) * 1000)
    html_bruto = html_bruto_total or "<!-- escalanet: 4 periodos raspados -->"
    return EscalaBruta(
        html_bruto=html_bruto,
        content_hash=hash_conteudo(html_bruto),
        celulas=celulas_total,
        duracao_ms=duracao,
        url_origem=ESCALANET_RELATORIO_URL,
        layout_mudou=layout_mudou,
    )


__all__ = ["ESCALANET_FUNCAO_PARA_CODIGO", "ESCALANET_PERIODOS", "raspar_por_data"]
