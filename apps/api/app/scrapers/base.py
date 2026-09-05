"""SINDESTIVA-PE · Tipos compartilhados pelos scrapers (Sprint 2).

Convenção: scrapers retornam uma `EscalaBruta` independente de fonte.
A normalização pra `lousa_escala_origem` + `lousa_alocacao` fica em
`app.services.scraping_service` — assim os scrapers são funções puras
sobre HTML (fáceis de mockar com `tests/fakes/*.html`).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CelulaBruta:
    """1 célula da lousa, normalizada pra (faina, função, matrícula, turno).

    Atributos:
        faina_codigo: código da faina (ex: "SALARIO", "PRODUCAO").
        funcao_codigo: código da função (ex: "MANDO_01", "TECNICA_04").
        trabalhador_matricula: matrícula OGMO do TPA escalado, ou None
            se a célula está vazia.
        turno_codigo: "DIURNO" ou "NOTURNO" (default "" — compat com
            scrapers que ainda não setam, ex: EscalaNet Sprint 3).
    """

    faina_codigo: str
    funcao_codigo: str
    trabalhador_matricula: str | None
    turno_codigo: str = ""


@dataclass(frozen=True, slots=True)
class EscalaBruta:
    """Resultado de 1 scrape (1 fonte × 1 porto × 1 turno × 1 data).

    Atributos:
        html_bruto: HTML original retornado pela fonte (sem normalização).
        content_hash: SHA-256 hex do `html_bruto` (64 chars).
        celulas: lista de células extraídas pelo parser tolerante.
        duracao_ms: tempo de execução do scrape em milissegundos.
        url_origem: URL exata que foi requisitada (None para MANUAL_FISCAL).
        layout_mudou: True se a estrutura do HTML diverge do esperado
            (3+ fallbacks acionados). Usado pra setar status=LAYOUT_MUDOU.
        erro_detalhes: mensagem de erro se o scrape falhou (None se OK).
    """

    html_bruto: str
    content_hash: str
    celulas: list[CelulaBruta] = field(default_factory=list)
    duracao_ms: int = 0
    url_origem: str | None = None
    layout_mudou: bool = False
    erro_detalhes: str | None = None


def hash_conteudo(html: str) -> str:
    """SHA-256 hex do conteúdo (canonizado em UTF-8, sem normalização de
    whitespace — preserva o bruto pra detectar mudança de layout real).
    """
    import hashlib

    return hashlib.sha256(html.encode("utf-8")).hexdigest()


__all__ = ["CelulaBruta", "EscalaBruta", "hash_conteudo"]
