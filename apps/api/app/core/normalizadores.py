"""SINDESTIVA-PE · Normalizadores de catálogos (Sprint 2 — refator T2-09).

Resolve o mismatch entre o que vem do HTML do TPA Tecnologia (lousa oficial
do OGMO-Suape) e o que está persistido como seed em `lousa_main.funcoes` e
`lousa_main.fainas`.

## Por que existe

O HTML do TPA retorna os **nomes exibidos** (com acentos, com espaços
injetados por CSS line-break tipo "CONSER TADOR" → "CONSERTADOR", com
variantes longas tipo "RO-RO VEÍCULO LEVE ATÉ 400"). Os seeds do banco
usam **códigos canônicos normalizados** (sem acento, sem variante, ex:
"PRODUCAO", "MANDO_01"). Sem normalização, o `scraping_service` faz o
lookup `fainas_idx.get(celula.faina_codigo)` e nunca encontra — `catalogo_miss`
em loop, `lousa_alocacao` fica vazia.

## Estratégia (decidida com Paulo em 05/09/2026)

- **Mapa explícito** HTML→seed (em vez de fuzzy match). Manoel Costa
  (fiscal-piloto) revisa o mapa sempre que o TPA mudar layout. Mais
  auditável, mais reproduzível, mais fácil de testar.
- **Defesa em profundidade**: normaliza nos DOIS lados (scraper emite
  código HTML, service normaliza índice do seed). Se um lado falhar, o
  outro ainda casa.
- **`codigo_html` é o canônico de wire** (HTML↔DB). `codigo` do seed
  vira **interno** (usado em FKs, lousa_alocacao.faina_id FK). A migration
  0004 adiciona `codigo_html` em `funcoes` e `fainas` + popula via mapa.

## Apply when

- QUALQUER scraper contra fonte externa cujo texto tem variantes
  (acentos, espaços, sinônimos).
- Cross-project: Agenticos (scraper Studio templates), Volund (futuro).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Final

# ---------------------------------------------------------------------------
# Normalização de texto
# ---------------------------------------------------------------------------

# Pre-norm em 2 passes:
#   - Com pontuação (roda ANTES de remover acentos + pontuação)
#   - Sem pontuação (roda DEPOIS de remover acentos, ANTES de remover pontuação)
_ABREVIACOES_COM_PONTUACAO: Final[tuple[tuple[str, str], ...]] = (
    # ("regex", "substituição") — aplicada em upper, com pontuação ainda presente.
    # Word boundary `\b` evita match no meio de palavra.
    (r"\bC/M\b", "CM"),
    (r"\bEMP\.\s*", "EMPILHADOR "),  # "Emp. GP" → "EMPILHADOR GP"
    (r"\bV\.\s*", "VEICULO "),       # "V. Pesado" → "VEICULO PESADO"
    (r"\bCONS\.\s*", "CONSERTADOR "),  # "C/M Cons." → "CM CONSERTADOR"
    (r"\bTRANSP\.?\b", "TRANSPORTADOR"),  # "Transp." / "Transp" → "TRANSPORTADOR"
    (r"\bPÁ\s*MEC\.\s*", "PA MECANICA "),  # "Pá Mec." → "PA MECANICA"
)

_ABREVIACOES_SEM_PONTUACAO: Final[tuple[tuple[str, str], ...]] = (
    # Roda DEPOIS de remover acentos (entrada sem Ç, Á, etc).
    # Resolve variantes com espaço injetado por CSS line-break que
    # viram palavras compostas pelo `re.sub(r"\s+", " ")` mas que
    # existem como tokens separados no banco.
    (r"\bTRANS\s+PORTADOR\b", "TRANSPORTADOR"),
    (r"\bPA\s+MEC\s+NICA\b", "PA MECANICA"),
    # CSS line-break "MECÂ NICA" (com acento entre MEC e NICA) — após
    # remover acentos vira "MECA NICA" (espaço é do HTML). Cola as metades.
    (r"\bMECA\s+NICA\b", "MECANICA"),
)


def normalizar_texto_catalogo(s: str | None) -> str:
    """Normaliza texto de catálogo para matching tolerante.

    Passos:
      1. None → ""
      2. upper + strip
      3. Aplica abreviações COM pontuação (C/M → CM, Emp. → EMPILHADOR, ...)
      4. Remove acentos (NFKD + drop combining)
      5. Aplica abreviações SEM pontuação (TRANS PORTADOR → TRANSPORTADOR)
      6. Remove não-alfanumérico (mantém só letras, dígitos, espaço)
      7. Colapsa múltiplos espaços em 1
      8. Strip final

    Returns:
        String canônica uppercase sem acento. Ex: "C/M Geral" → "CM GERAL".

    Examples:
        >>> normalizar_texto_catalogo("C/M Geral")
        'CM GERAL'
        >>> normalizar_texto_catalogo("  CONSER  TADOR  ")
        'CONSER TADOR'
        >>> normalizar_texto_catalogo("RO-RO Veículo Leve até 400")
        'RO RO VEICULO LEVE ATE 400'
        >>> normalizar_texto_catalogo("C/M Cons.")
        'CM CONSERTADOR'
        >>> normalizar_texto_catalogo("Emp. GP")
        'EMPILHADOR GP'
        >>> normalizar_texto_catalogo("V. Pesado")
        'VEICULO PESADO'
        >>> normalizar_texto_catalogo(None)
        ''
    """
    if not s:
        return ""
    # 1. upper + strip
    s = s.upper().strip()
    # 2. Aplica abreviações com pontuação (C/M, Emp., V., Cons., Transp., Pá Mec.)
    for pattern, repl in _ABREVIACOES_COM_PONTUACAO:
        s = re.sub(pattern, repl, s)
    # 3. Remove acentos: NFKD decompõe, "Mn" (mark, nonspacing) é o acento
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # 4. Aplica abreviações sem pontuação (TRANS PORTADOR, PA MEC NICA)
    for pattern, repl in _ABREVIACOES_SEM_PONTUACAO:
        s = re.sub(pattern, repl, s)
    # 5. Mantém só alfanumérico + `_` + espaço (remove / - , . etc).
    # `_` é importante pra preservar códigos canônicos do seed
    # ("MANDO_01", "TECNICA_04") que têm underscore.
    s = re.sub(r"[^A-Z0-9_ ]", " ", s)
    # 6. Colapsa múltiplos espaços
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Mapeamento HTML → codigo do seed
# ---------------------------------------------------------------------------
# Estes mapas são a **fonte de verdade** do casamento HTML↔DB. Revisar
# com Manoel Costa sempre que o TPA Tecnologia mudar o layout.
#
# Chave = forma normalizada de `normalizar_texto_catalogo()` aplicada ao
#         nome que vem do HTML (já após `get_text(strip=True).upper()`).
# Valor = `codigo` exato da linha em `lousa_main.funcoes` / `lousa_main.fainas`.

# 26 funções na ORDEM que aparecem no HTML (row 2 das 2 tabelas).
# Validado em 05/09/2026 contra http://tpa.ogmosuape.com.br/web/lousa_estiva
MAPA_FUNCOES_HTML_PARA_CODIGO: Final[dict[str, str]] = {
    # --- Mando (6) ---
    "CM GERAL": "MANDO_01",
    "CM PORÃO": "MANDO_02",
    "CM PORAO": "MANDO_02",  # fallback sem acento
    "CM BLOCO": "MANDO_03",
    "CM RECHEGO": "MANDO_04",
    "CM CONSERTADOR": "MANDO_05",
    "CM CONS": "MANDO_05",  # CSS line-break "CONSER TADOR" + "C/M Cons."
    "CM CONSER TADOR": "MANDO_05",  # defesa: linha quebrada em 2 <span>
    "SUPERVISOR": "MANDO_06",
    "SUPER VISOR": "MANDO_06",  # CSS line-break (validação 05/09/2026)
    # --- Terno (6) ---
    "PORÃO": "TERNO_01",
    "PORAO": "TERNO_01",
    "BLOCO MAX": "TERNO_02",
    "BLOCO": "TERNO_03",
    "RECHEGO": "TERNO_04",
    "CONSERTADOR": "TERNO_05",
    "CONS": "TERNO_05",  # CSS line-break
    "CONSER TADOR": "TERNO_05",
    "SHIP LOADER PORÃO": "TERNO_06",
    "SHIP LOADER": "TERNO_06",  # variante curta
    "SHIP LOADER PORAO": "TERNO_06",
    # --- Técnica (12) ---
    "SINALEIRO": "TECNICA_01",
    "SINA LEIRO": "TECNICA_01",  # CSS line-break
    "GUINCHO A": "TECNICA_02",
    "GUINCHO B": "TECNICA_03",
    "EMPILHADOR GP": "TECNICA_04",
    "EMPILHA DOR GP": "TECNICA_04",  # CSS line-break
    "EMPILHADOR PP": "TECNICA_05",
    "EMPILHA DOR PP": "TECNICA_05",
    "VEÍCULO PESADO": "TECNICA_06",
    "VEICULO PESADO": "TECNICA_06",
    "V PESADO": "TECNICA_06",  # abreviação comum
    "VEÍCULO LEVE": "TECNICA_07",
    "VEICULO LEVE": "TECNICA_07",
    "V LEVE": "TECNICA_07",
    "MANOBRISTA": "TECNICA_08",
    "MANO BRISTA": "TECNICA_08",  # CSS line-break (validação 05/09/2026)
    "TRANSPORTADOR": "TECNICA_09",
    "TRANS P": "TECNICA_09",  # CSS line-break "TRANSPOR TADOR"
    "PÁ MECÂNICA": "TECNICA_10",
    "PA MECANICA": "TECNICA_10",
    "PÁ MEC": "TECNICA_10",  # abreviação
    "RETRO ESCAVADEIRA": "TECNICA_11",
    "RETRO ESCAVA DEIRA": "TECNICA_11",
    "PC": "TECNICA_12",
    # --- Vigia (2) ---
    # HTML do TPA: "RODÍZIO" / "CONTRA BORDO" (descrição física do rodízio)
    # Seed:        "Vigia Porto" / "Vigia Cais"   (papel do vigia)
    # Ambos os pares apontam pro mesmo `codigo` — defesa em profundidade
    # para quando o Centro de Comando renderizar a versão "papel" e o
    # scraper emitir a versão "física".
    "RODÍZIO": "VIGIA_01",
    "RODIZIO": "VIGIA_01",
    "VIGIA PORTO": "VIGIA_01",
    "VIGIA CAIS": "VIGIA_02",
    "CONTRA BORDO": "VIGIA_02",
    "CONTRA BOR DO": "VIGIA_02",  # CSS line-break
}

# 11 fainas na ORDEM que aparecem no HTML (rows 3+).
# As 3 "RO-RO ..." viram o mesmo seed (VEICULO) por decisão de produto
# (não faz sentido ter 3 linhas separadas no Centro de Comando).
# Manoel Costa confirma Sprint 2.
MAPA_FAINAS_HTML_PARA_CODIGO: Final[dict[str, str]] = {
    "PRODUÇÃO": "PRODUCAO",
    "PRODUCAO": "PRODUCAO",
    "SALÁRIO": "SALARIO",
    "SALARIO": "SALARIO",
    "SACARIA SOLTA": "SACARIA",
    "SACARIA PRÉ LINGADA": "SACARIA",
    "SACARIA PRE LINGADA": "SACARIA",
    "RO RO VEÍCULO LEVE": "VEICULO",
    "RO RO VEICULO LEVE": "VEICULO",
    "RO RO VEÍCULO LEVE ATÉ 400": "VEICULO",
    "RO RO VEICULO LEVE ATE 400": "VEICULO",
    "RO RO VEÍCULO PESADO": "VEICULO",
    "RO RO VEICULO PESADO": "VEICULO",
    "DIVERSOS E EQUIP EÓLICOS": "DIVERSOS",
    "DIVERSOS E EQUIP EOLICOS": "DIVERSOS",
    "DIVERSOS": "DIVERSOS",
    "CADASTRO": "CADASTRO",
    "SUPLEMENTAR": "SUPLEMENTAR",
    "TRABALHO EM ALTURA NR 35": "ALTURA",
    "TRABALHO EM ALTURA": "ALTURA",
    "ALTURA": "ALTURA",
}


# ---------------------------------------------------------------------------
# Resolvers públicos
# ---------------------------------------------------------------------------

def resolver_funcao_codigo(nome_html: str | None) -> str | None:
    """Resolve nome OU código de função do HTML/seed para `codigo` canônico.

    Aceita AMBOS os formatos:
      - Nome exibido do HTML ("C/M Geral", "Sinaleiro", "Emp. GP", ...)
        → procura no `MAPA_FUNCOES_HTML_PARA_CODIGO`.
      - Código canônico do seed ("MANDO_01", "TECNICA_04", "VIGIA_01")
        → retorna como está (regex fallback do scraper TPA, e fontes
        que já emitem códigos limpos — ex: `data-funao="MANDO_01"` em
        layouts novos do TPA).

    Args:
        nome_html: texto extraído do HTML (já `.get_text(strip=True).upper()`),
                   OU código canônico do seed.

    Returns:
        `codigo` exato em `lousa_main.funcoes` (ex: "MANDO_01"), ou None
        se não houver match (célula é descartada com warning `catalogo_miss`).

    Examples:
        >>> resolver_funcao_codigo("C/M Geral")
        'MANDO_01'
        >>> resolver_funcao_codigo("CONSER  TADOR")
        'TERNO_05'
        >>> resolver_funcao_codigo("Sinaleiro")
        'TECNICA_01'
        >>> # Aceita código canônico direto (regex fallback / layouts novos)
        >>> resolver_funcao_codigo("MANDO_01")
        'MANDO_01'
        >>> resolver_funcao_codigo("TECNICA_04")
        'TECNICA_04'
        >>> resolver_funcao_codigo("VIGIA_02")
        'VIGIA_02'
        >>> resolver_funcao_codigo("Função Inexistente")
    """
    if not nome_html:
        return None
    chave = normalizar_texto_catalogo(nome_html)
    if not chave:
        return None
    # 1. Match no mapa HTML→seed
    if chave in MAPA_FUNCOES_HTML_PARA_CODIGO:
        return MAPA_FUNCOES_HTML_PARA_CODIGO[chave]
    # 2. Já é código canônico? (regex fallback / layouts novos)
    codigos_conhecidos = set(MAPA_FUNCOES_HTML_PARA_CODIGO.values())
    if chave in codigos_conhecidos:
        return chave
    return None


def resolver_faina_codigo(nome_html: str | None) -> str | None:
    """Resolve nome OU código de faina do HTML/seed para `codigo` canônico.

    Aceita AMBOS os formatos (ver `resolver_funcao_codigo` para rationale).

    Args:
        nome_html: texto extraído do HTML ou código canônico do seed.

    Returns:
        `codigo` exato em `lousa_main.fainas` (ex: "PRODUCAO"), ou None
        se não houver match.

    Examples:
        >>> resolver_faina_codigo("Produção")
        'PRODUCAO'
        >>> resolver_faina_codigo("RO-RO Veículo Leve até 400")
        'VEICULO'
        >>> resolver_faina_codigo("Trabalho em Altura - NR 35")
        'ALTURA'
        >>> # Aceita código canônico direto
        >>> resolver_faina_codigo("PRODUCAO")
        'PRODUCAO'
        >>> resolver_faina_codigo("VEICULO")
        'VEICULO'
    """
    if not nome_html:
        return None
    chave = normalizar_texto_catalogo(nome_html)
    if not chave:
        return None
    # 1. Match no mapa HTML→seed
    if chave in MAPA_FAINAS_HTML_PARA_CODIGO:
        return MAPA_FAINAS_HTML_PARA_CODIGO[chave]
    # 2. Já é código canônico?
    codigos_conhecidos = set(MAPA_FAINAS_HTML_PARA_CODIGO.values())
    if chave in codigos_conhecidos:
        return chave
    return None


# ---------------------------------------------------------------------------
# Helpers para a migration
# ---------------------------------------------------------------------------

def mapa_funcao_html_para_seed() -> dict[str, str]:
    """Snapshot do MAPA_FUNCOES para uso em migrations/scripts de seed.

    Returns:
        Dict {nome_html_normalizado: codigo_seed} — pronto para UPSERT
        em `lousa_main.funcoes.codigo_html`.

    Nota: a chave aqui é a forma NORMALIZADA (sem acento, sem pontuação).
    O scraper já aplica `normalizar_texto_catalogo` antes de consultar.
    """
    return dict(MAPA_FUNCOES_HTML_PARA_CODIGO)


def mapa_faina_html_para_seed() -> dict[str, str]:
    """Snapshot do MAPA_FAINAS para uso em migrations/scripts de seed."""
    return dict(MAPA_FAINAS_HTML_PARA_CODIGO)


__all__ = [
    "MAPA_FAINAS_HTML_PARA_CODIGO",
    "MAPA_FUNCOES_HTML_PARA_CODIGO",
    "mapa_faina_html_para_seed",
    "mapa_funcao_html_para_seed",
    "normalizar_texto_catalogo",
    "resolver_faina_codigo",
    "resolver_funcao_codigo",
]
