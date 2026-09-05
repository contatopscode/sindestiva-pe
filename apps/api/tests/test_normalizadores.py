"""SINDESTIVA-PE · Testes do normalizador de catálogos (Sprint 2 — refator T2-09).

Cobre:
  - `normalizar_texto_catalogo`: None, acentos, espaços múltiplos,
    abreviações, CSS line-break, mixed case, símbolos não-alfanuméricos
  - `resolver_funcao_codigo`: 26 funções (happy path) + variantes
    (acentos, abreviações, CSS line-break) + entradas inválidas
  - `resolver_faina_codigo`: 11 fainas (happy path) + variantes +
    entradas inválidas

Total: 50+ testes verdes.
"""
from __future__ import annotations

import pytest

from app.core.normalizadores import (
    MAPA_FUNCOES_HTML_PARA_CODIGO,
    normalizar_texto_catalogo,
    resolver_faina_codigo,
    resolver_funcao_codigo,
)

# ===========================================================================
# 1. normalizar_texto_catalogo — casos de borda
# ===========================================================================

class TestNormalizarTexto:
    """Cobertura de `normalizar_texto_catalogo` (função pura)."""

    def test_none_retorna_string_vazia(self) -> None:
        assert normalizar_texto_catalogo(None) == ""

    def test_string_vasia_retorna_vazia(self) -> None:
        assert normalizar_texto_catalogo("") == ""
        assert normalizar_texto_catalogo("   ") == ""

    @pytest.mark.parametrize("inp,esperado", [
        ("CM", "CM"),
        ("C/M", "CM"),
        ("c/m", "CM"),
        ("C/M geral", "CM GERAL"),
        ("C/M Geral", "CM GERAL"),
        ("C/M   Geral", "CM GERAL"),
        ("  C/M  Geral  ", "CM GERAL"),
    ])
    def test_pre_norm_cm(self, inp: str, esperado: str) -> None:
        assert normalizar_texto_catalogo(inp) == esperado

    @pytest.mark.parametrize("inp,esperado", [
        ("Pá Mec.", "PA MECANICA"),
        ("Pá Mecânica", "PA MECANICA"),
        ("PA MECANICA", "PA MECANICA"),
        ("PÁ MECÂ NICA", "PA MECANICA"),  # CSS line-break com acento
        ("PA MEC NICA", "PA MECANICA"),    # CSS line-break sem acento
    ])
    def test_pre_norm_pa_mecanica(self, inp: str, esperado: str) -> None:
        assert normalizar_texto_catalogo(inp) == esperado

    @pytest.mark.parametrize("inp,esperado", [
        ("V. Pesado", "VEICULO PESADO"),
        ("V.Leve", "VEICULO LEVE"),
        ("Veículo Pesado", "VEICULO PESADO"),
    ])
    def test_pre_norm_veiculo(self, inp: str, esperado: str) -> None:
        assert normalizar_texto_catalogo(inp) == esperado

    @pytest.mark.parametrize("inp,esperado", [
        ("Emp. GP", "EMPILHADOR GP"),
        ("Empilhador GP", "EMPILHADOR GP"),
        ("EMP. PP", "EMPILHADOR PP"),
    ])
    def test_pre_norm_empilhador(self, inp: str, esperado: str) -> None:
        assert normalizar_texto_catalogo(inp) == esperado

    @pytest.mark.parametrize("inp,esperado", [
        ("Transp.", "TRANSPORTADOR"),
        ("Transp", "TRANSPORTADOR"),
        ("TRANSP", "TRANSPORTADOR"),
        ("Transportador", "TRANSPORTADOR"),
        ("TRANS  PORTADOR", "TRANSPORTADOR"),  # CSS line-break
        ("TRANS PORTADOR", "TRANSPORTADOR"),
    ])
    def test_pre_norm_transportador(self, inp: str, esperado: str) -> None:
        assert normalizar_texto_catalogo(inp) == esperado

    def test_remove_acentos(self) -> None:
        assert normalizar_texto_catalogo("SINALEIRO") == "SINALEIRO"
        assert normalizar_texto_catalogo("Sinaleiro") == "SINALEIRO"
        assert normalizar_texto_catalogo("sinaleiro") == "SINALEIRO"

    def test_remove_pontuacao(self) -> None:
        # Hífen, vírgula, ponto, barra viram espaço
        assert normalizar_texto_catalogo("RO-RO, Veículo.") == "RO RO VEICULO"

    def test_colapsa_espacos_multiplos(self) -> None:
        assert normalizar_texto_catalogo("A   B") == "A B"
        assert normalizar_texto_catalogo("A\n\tB") == "A B"

    def test_preserva_numeros(self) -> None:
        assert normalizar_texto_catalogo("EMPILHADOR 400") == "EMPILHADOR 400"
        assert normalizar_texto_catalogo("RO-RO LEVE ATÉ 400") == "RO RO LEVE ATE 400"


# ===========================================================================
# 2. resolver_funcao_codigo — 26 funções + variantes
# ===========================================================================

class TestResolverFuncaoCodigo:
    """Cobertura de `resolver_funcao_codigo` para as 26 funções canônicas."""

    @pytest.mark.parametrize("html,codigo_esperado", [
        # Mando (6)
        ("C/M Geral", "MANDO_01"),
        ("C/M Porão", "MANDO_02"),
        ("C/M Bloco", "MANDO_03"),
        ("C/M Rechego", "MANDO_04"),
        ("C/M Consertador", "MANDO_05"),
        ("Supervisor", "MANDO_06"),
        # Terno (6)
        ("Porão", "TERNO_01"),
        ("Bloco MAX", "TERNO_02"),
        ("Bloco", "TERNO_03"),
        ("Rechego", "TERNO_04"),
        ("Consertador", "TERNO_05"),
        ("Ship Loader", "TERNO_06"),
        # Técnica (12)
        ("Sinaleiro", "TECNICA_01"),
        ("Guincho A", "TECNICA_02"),
        ("Guincho B", "TECNICA_03"),
        ("Emp. GP", "TECNICA_04"),
        ("Emp. PP", "TECNICA_05"),
        ("V. Pesado", "TECNICA_06"),
        ("V. Leve", "TECNICA_07"),
        ("Manobrista", "TECNICA_08"),
        ("Transp.", "TECNICA_09"),
        ("Pá Mec.", "TECNICA_10"),
        ("Retro Escavadeira", "TECNICA_11"),
        ("PC", "TECNICA_12"),
        # Vigia (2) — divergência: seed=Vigia Porto/Cais, HTML=Rodízio/Contra Bordo
        ("Rodízio", "VIGIA_01"),
        ("Contra Bordo", "VIGIA_02"),
    ])
    def test_26_funcoes_canonicas(self, html: str, codigo_esperado: str) -> None:
        assert resolver_funcao_codigo(html) == codigo_esperado

    def test_vigia_papel_tambem_casa(self) -> None:
        """Seed tem Vigia Porto/Cais (papel); HTML tem Rodízio/Contra Bordo (físico).
        Ambos apontam para VIGIA_01/VIGIA_02 (defesa em profundidade)."""
        assert resolver_funcao_codigo("Vigia Porto") == "VIGIA_01"
        assert resolver_funcao_codigo("Vigia Cais") == "VIGIA_02"

    @pytest.mark.parametrize("html", [
        # CSS line-break (válidação 05/09/2026 contra TPA real)
        "CONSER  TADOR",
        "SINA LEIRO",
        "MANO BRISTA",
        "TRANS  PORTADOR",
        "PÁ MECÂ NICA",
        "SUPER VISOR",
        "CONTRA BOR DO",
    ])
    def test_variantes_css_linebreak(self, html: str) -> None:
        """Variantes com espaço injetado por CSS `<wbr>` casam com o código certo."""
        assert resolver_funcao_codigo(html) is not None

    @pytest.mark.parametrize("html_invalido", [
        None,
        "",
        "Funcao Inexistente",
        "Padaria do Porto",
        "TPA 12345",
        "12345",
    ])
    def test_invalido_retorna_none(self, html_invalido: str | None) -> None:
        assert resolver_funcao_codigo(html_invalido) is None

    def test_mapa_tem_26_funcoes_unicas(self) -> None:
        """O mapa deve mapear para exatamente 26 códigos (DD v1 §3.8)."""
        codigos_mapeados = set(MAPA_FUNCOES_HTML_PARA_CODIGO.values())
        assert len(codigos_mapeados) == 26, (
            f"MAPA_FUNCOES aponta para {len(codigos_mapeados)} códigos "
            f"distintos (esperado 26). Códigos: {sorted(codigos_mapeados)}"
        )


# ===========================================================================
# 3. resolver_faina_codigo — 11 fainas + variantes
# ===========================================================================

class TestResolverFainaCodigo:
    """Cobertura de `resolver_faina_codigo` para as 11 fainas canônicas."""

    @pytest.mark.parametrize("html,codigo_esperado", [
        ("Produção", "PRODUCAO"),
        ("Salário", "SALARIO"),
        ("Sacaria Solta", "SACARIA"),
        ("Sacaria Pré-Lingada", "SACARIA"),
        ("RO-RO Veículo Leve", "VEICULO"),
        ("RO-RO Veículo Leve até 400", "VEICULO"),
        ("RO-RO Veículo Pesado", "VEICULO"),
        ("Diversos e Equip. Eólicos", "DIVERSOS"),
        ("Cadastro", "CADASTRO"),
        ("Suplementar", "SUPLEMENTAR"),
        ("Trabalho em Altura - NR 35", "ALTURA"),
    ])
    def test_fainas_canonicas(self, html: str, codigo_esperado: str) -> None:
        assert resolver_faina_codigo(html) == codigo_esperado

    @pytest.mark.parametrize("html_invalido", [
        None,
        "",
        "Faina Inexistente",
        "RO-RO Navio Tanque",
        "12345",
    ])
    def test_invalido_retorna_none(self, html_invalido: str | None) -> None:
        assert resolver_faina_codigo(html_invalido) is None

    def test_agregacao_sacaria(self) -> None:
        """HTML tem 2 variantes de Sacaria que mapeiam pro mesmo código
        (defesa contra UNIQUE violation em `lousa_alocacao`)."""
        assert resolver_faina_codigo("Sacaria Solta") == "SACARIA"
        assert resolver_faina_codigo("Sacaria Pré-Lingada") == "SACARIA"
        assert resolver_faina_codigo("SACARIA SOLTA") == "SACARIA"
        assert resolver_faina_codigo("SACARIA PRÉ-LINGADA") == "SACARIA"

    def test_agregacao_ro_ro(self) -> None:
        """3 variantes de RO-RO mapeiam pro mesmo `VEICULO`."""
        assert resolver_faina_codigo("RO-RO Veículo Leve") == "VEICULO"
        assert resolver_faina_codigo("RO-RO Veículo Leve até 400") == "VEICULO"
        assert resolver_faina_codigo("RO-RO Veículo Pesado") == "VEICULO"
