"""SINDESTIVA-PE · Testes do BI & Dashboards (Sprint 7).

Cobre:
  - Funções puras (não dependem de DB): 8 cenários
  - I/O + cache: 2 cenários (smoke)
  - Endpoints via API live: 5 cenários (RBAC + KPIs + drill-down)

Total: 15 cenários verdes.

Convenção de naming: `test_bi_puro_*` pra funções puras,
`test_bi_io_*` pra I/O, `test_bi_api_*` pra integração com API live.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.services import bi_service
from app.services.bi_service import (
    Periodo,
    RemanejamentoResumo,
    THRESHOLD_TPA_REMANEJADO,
    TOP_N_REMANEJADOS,
    VALOR_HORA_DEFAULT,
    agrupar_remanejamentos_por_dia,
    calcular_causa_principal,
    calcular_comparecimento,
    calcular_folha_paga,
    calcular_percentual_nack,
    gerar_insights,
    top_cais_problematico,
    top_funcao_remanejada,
    top_horario_critico,
    top_remanejados,
)


# ---------------------------------------------------------------------------
# 1. Funções puras — comparecimento (T7-01 KPI 1)
# ---------------------------------------------------------------------------


def test_bi_puro_comparecimento_normal() -> None:
    """50 confirmados de 100 escalados = 50%."""
    result = calcular_comparecimento(total_escalados=100, total_confirmados=50)
    assert result["total_escalados"] == 100
    assert result["total_confirmados"] == 50
    assert result["total_ausentes"] == 50
    assert result["percentual"] == 50.0


def test_bi_puro_comparecimento_zero_escalados() -> None:
    """Sem escalados → percentual = 0 (sem divisão por zero)."""
    result = calcular_comparecimento(total_escalados=0, total_confirmados=0)
    assert result["percentual"] == 0.0
    assert result["total_ausentes"] == 0


def test_bi_puro_comparecimento_cap_defesa() -> None:
    """Confirmados > escalados (edge case) → cap em escalados."""
    result = calcular_comparecimento(total_escalados=10, total_confirmados=15)
    assert result["total_confirmados"] == 10  # cap
    assert result["percentual"] == 100.0


def test_bi_puro_comparecimento_negativo_rejeita() -> None:
    """Totais negativos → ValueError."""
    with pytest.raises(ValueError, match="negativos"):
        calcular_comparecimento(total_escalados=-1, total_confirmados=0)


# ---------------------------------------------------------------------------
# 2. Funções puras — folha paga (T7-01 KPI 2)
# ---------------------------------------------------------------------------


def test_bi_puro_folha_paga_calculo_basico() -> None:
    """10 remanejamentos × R$ 25/h × 8h = R$ 2.000."""
    periodo = Periodo(inicio=date(2026, 9, 1), fim=date(2026, 9, 30))
    result = calcular_folha_paga(total_remanejamentos=10, periodo=periodo)
    assert result["valor_total_brl"] == 2000.0
    assert result["total_remanejamentos"] == 10
    assert result["valor_medio_remanejamento_brl"] == 200.0


def test_bi_puro_folha_paga_zero() -> None:
    """0 remanejamentos → R$ 0."""
    periodo = Periodo(inicio=date(2026, 9, 1), fim=date(2026, 9, 1))
    result = calcular_folha_paga(total_remanejamentos=0, periodo=periodo)
    assert result["valor_total_brl"] == 0.0
    assert result["valor_medio_remanejamento_brl"] == VALOR_HORA_DEFAULT * 8


# ---------------------------------------------------------------------------
# 3. Funções puras — causa principal (T7-01 KPI 3)
# ---------------------------------------------------------------------------


def test_bi_puro_causa_principal_mais_frequente() -> None:
    """5 motivos, ATESTADO aparece 3× → é a causa principal."""
    motivos = [
        "ATESTADO_MEDICO", "ATESTADO_MEDICO", "ATESTADO_MEDICO",
        "OUTRO", "OUTRO",
    ]
    result = calcular_causa_principal(motivos)
    assert result["motivo"] == "ATESTADO_MEDICO"
    assert result["total"] == 3
    assert result["percentual"] == 60.0


def test_bi_puro_causa_principal_lista_vazia() -> None:
    """Sem dados → placeholder OUTRO com 0."""
    result = calcular_causa_principal([])
    assert result["motivo"] == "OUTRO"
    assert result["total"] == 0
    assert result["percentual"] == 0.0


# ---------------------------------------------------------------------------
# 4. Funções puras — % NACK (T7-01 KPI 4)
# ---------------------------------------------------------------------------


def test_bi_puro_nack_normal() -> None:
    """1 NACK de 10 notificados = 10%."""
    result = calcular_percentual_nack(total_notificados=10, total_nack=1)
    assert result["percentual"] == 10.0


def test_bi_puro_nack_zero_notificados() -> None:
    """0 notificados → 0% (sem divisão por zero)."""
    result = calcular_percentual_nack(total_notificados=0, total_nack=0)
    assert result["percentual"] == 0.0


# ---------------------------------------------------------------------------
# 5. Funções puras — série temporal (T7-02)
# ---------------------------------------------------------------------------


def _r(
    data: date,
    *,
    tpa_nome: str = "TPA Teste",
    motivo: str = "OUTRO",
    cais: str | None = "Cais 1",
    turno: str = "DIURNO",
    funcao: str = "CONFERENTE",
) -> RemanejamentoResumo:
    """Helper: cria RemanejamentoResumo fake."""
    return RemanejamentoResumo(
        id=uuid4(),
        codigo_se=f"SE-{data.strftime('%Y%m%d')}-001",
        data_referencia=data,
        tpa_out_id=uuid4(),
        tpa_out_nome=tpa_nome,
        tpa_out_matricula=f"OG-{tpa_nome[:4].upper()}",
        funcao_origem_id=uuid4(),
        funcao_origem_nome=funcao,
        cais_origem=cais,
        turno_id=uuid4(),
        turno_codigo=turno,
        motivo=motivo,
        status="PENDENTE",
        created_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
    )


def test_bi_puro_por_dia_preenche_buracos() -> None:
    """Período 7 dias, só 1 dia tem dados → gráfico tem 7 pontos."""
    periodo = Periodo(inicio=date(2026, 9, 1), fim=date(2026, 9, 7))
    rems = [_r(date(2026, 9, 3))]
    result = agrupar_remanejamentos_por_dia(rems, periodo=periodo)
    assert len(result["items"]) == 7  # 7 dias preenchidos
    assert result["total"] == 1
    assert result["media_diaria"] == round(1 / 7, 2)
    # Dia 3 (idx 2) tem 1, resto 0.
    assert result["items"][2]["total"] == 1
    assert result["items"][0]["total"] == 0


def test_bi_puro_por_dia_ignora_fora_do_periodo() -> None:
    """Remanejamento fora do período é descartado."""
    periodo = Periodo(inicio=date(2026, 9, 1), fim=date(2026, 9, 3))
    rems = [
        _r(date(2026, 9, 1)),
        _r(date(2026, 8, 30)),  # fora
        _r(date(2026, 9, 3)),
    ]
    result = agrupar_remanejamentos_por_dia(rems, periodo=periodo)
    assert result["total"] == 2


# ---------------------------------------------------------------------------
# 6. Funções puras — top remanejados (T7-04)
# ---------------------------------------------------------------------------


def test_bi_puro_top_remanejados_ordenado() -> None:
    """TPA A com 3, TPA B com 1 → A primeiro."""
    tpa_a = uuid4()
    tpa_b = uuid4()
    rems = [
        _r(date(2026, 9, 1), tpa_nome="Alice"),
        _r(date(2026, 9, 2), tpa_nome="Alice"),
        _r(date(2026, 9, 3), tpa_nome="Alice"),
        _r(date(2026, 9, 4), tpa_nome="Bob"),
    ]
    # Reatribui IDs pra teste (helper gera random).
    rems[0] = RemanejamentoResumo(
        **{**rems[0].__dict__, "tpa_out_id": tpa_a, "tpa_out_nome": "Alice"}
    )
    rems[1] = RemanejamentoResumo(
        **{**rems[1].__dict__, "tpa_out_id": tpa_a, "tpa_out_nome": "Alice"}
    )
    rems[2] = RemanejamentoResumo(
        **{**rems[2].__dict__, "tpa_out_id": tpa_a, "tpa_out_nome": "Alice"}
    )
    rems[3] = RemanejamentoResumo(
        **{**rems[3].__dict__, "tpa_out_id": tpa_b, "tpa_out_nome": "Bob"}
    )
    ranking = top_remanejados(rems, n=TOP_N_REMANEJADOS)
    assert len(ranking) == 2
    assert ranking[0]["tpa_nome"] == "Alice"
    assert ranking[0]["total_remanejamentos"] == 3
    assert ranking[1]["tpa_nome"] == "Bob"
    assert ranking[1]["total_remanejamentos"] == 1


def test_bi_puro_top_remanejados_respeita_n() -> None:
    """n=2 retorna só top 2 mesmo com 5 TPAs diferentes."""
    rems = [
        _r(date(2026, 9, 1), tpa_nome=f"TPA{i}") for i in range(5)
    ]
    # Cada TPA tem só 1 remanejamento → ranking é arbitrário mas n=2.
    ranking = top_remanejados(rems, n=2)
    assert len(ranking) == 2


# ---------------------------------------------------------------------------
# 7. Funções puras — top cards (T7-03)
# ---------------------------------------------------------------------------


def test_bi_puro_top_cards_funcao_cais_horario() -> None:
    """Função CONFERENTE × 6 (5+1), Cais 3 × 5, DIURNO × 6."""
    rems = (
        [_r(date(2026, 9, 1), funcao="CONFERENTE", cais="Cais 3", turno="DIURNO")] * 5
        + [_r(date(2026, 9, 2), funcao="ARRUMADOR", cais="Cais 1", turno="NOTURNO")] * 2
        + [_r(date(2026, 9, 3), funcao="CONFERENTE", cais="Cais 1", turno="DIURNO")]
    )
    func = top_funcao_remanejada(rems)
    assert func is not None
    assert func["label"] == "CONFERENTE"
    assert func["total"] == 6
    assert func["percentual"] == round(6 / 8 * 100, 2)

    cais = top_cais_problematico(rems)
    assert cais is not None
    assert cais["label"] == "Cais 3"
    assert cais["total"] == 5  # 5 (Cais 3/Diurno) > 3 (Cais 1/Noturno+Diurno)
    assert cais["percentual"] == round(5 / 8 * 100, 2)

    hor = top_horario_critico(rems)
    assert hor is not None
    assert hor["label"] == "DIURNO"
    assert hor["total"] == 6


def test_bi_puro_top_cards_vazio_retorna_none() -> None:
    """Sem remanejamentos → cards = None."""
    assert top_funcao_remanejada([]) is None
    assert top_cais_problematico([]) is None
    assert top_horario_critico([]) is None


# ---------------------------------------------------------------------------
# 8. Funções puras — insights (T7-05)
# ---------------------------------------------------------------------------


def test_bi_puro_insights_tpa_5_vezes_gera_alerta() -> None:
    """TPA com 5+ remanejamentos → insight de alerta."""
    tpa = uuid4()
    rems = []
    for i in range(THRESHOLD_TPA_REMANEJADO + 1):
        r = _r(date(2026, 9, i + 1), tpa_nome="Sobrecarregado")
        rems.append(
            RemanejamentoResumo(**{**r.__dict__, "tpa_out_id": tpa, "tpa_out_nome": "Sobrecarregado"})
        )
    periodo = Periodo(inicio=date(2026, 9, 1), fim=date(2026, 9, 30))
    insights = gerar_insights(rems, periodo=periodo)
    regras = [i["regra"] for i in insights]
    assert "TPA_REMANEJADO_5_VEZES" in regras
    alerta = next(i for i in insights if i["regra"] == "TPA_REMANEJADO_5_VEZES")
    assert alerta["severidade"] == "alerta"
    assert alerta["tpa_nome"] == "Sobrecarregado"
    assert alerta["total"] == THRESHOLD_TPA_REMANEJADO + 1


def test_bi_puro_insights_motivo_concentrado_gera_alerta() -> None:
    """Motivo > 30% do total → insight de alerta."""
    rems = (
        [_r(date(2026, 9, 1), motivo="ATESTADO_MEDICO")] * 7
        + [_r(date(2026, 9, 2), motivo="OUTRO")] * 3
    )
    periodo = Periodo(inicio=date(2026, 9, 1), fim=date(2026, 9, 30))
    insights = gerar_insights(rems, periodo=periodo)
    motivo_ins = next(
        (i for i in insights if i["regra"] == "MOTIVO_CONCENTRADO"), None
    )
    assert motivo_ins is not None
    assert motivo_ins["severidade"] == "alerta"
    assert "ATESTADO_MEDICO" in motivo_ins["mensagem"]


def test_bi_puro_insights_pico_detectado() -> None:
    """Dia com 5+ remanejamentos × 3× média → insight PICO_DIA."""
    rems = []
    # Dia 1: 6 remanejamentos (pico), outros dias: 0.
    for i in range(6):
        rems.append(_r(date(2026, 9, 1)))
    periodo = Periodo(inicio=date(2026, 9, 1), fim=date(2026, 9, 7))
    insights = gerar_insights(rems, periodo=periodo)
    pico = next((i for i in insights if i["regra"] == "PICO_DIA"), None)
    assert pico is not None
    assert "2026-09-01" in pico["mensagem"]


# ---------------------------------------------------------------------------
# 9. Periodo
# ---------------------------------------------------------------------------


def test_bi_puro_periodo_ultimos_dias_valido() -> None:
    """Periodo.ultimos_dias(7) gera [ref-6, ref]."""
    p = Periodo.ultimos_dias(7, ref=date(2026, 9, 2))
    assert p.inicio == date(2026, 8, 27)
    assert p.fim == date(2026, 9, 2)


def test_bi_puro_periodo_invalido_rejeita() -> None:
    """Periodo.ultimos_dias(15) → ValueError (não está em PERIODOS_VALIDOS)."""
    with pytest.raises(ValueError, match="não suportado"):
        Periodo.ultimos_dias(15)


# ---------------------------------------------------------------------------
# 10. Constantes expostas
# ---------------------------------------------------------------------------


def test_bi_puro_constantes_presentes() -> None:
    """Constantes usadas pelos endpoints estão exportadas."""
    assert bi_service.VALOR_HORA_DEFAULT == 25.0
    assert bi_service.HORAS_POR_REMANEJAMENTO == 8
    assert 7 in bi_service.PERIODOS_VALIDOS
    assert 365 in bi_service.PERIODOS_VALIDOS
    assert bi_service.THRESHOLD_TPA_REMANEJADO == 5
    assert bi_service.CACHE_TTL_SEGUNDOS == 300


# ---------------------------------------------------------------------------
# 11. Smoke I/O — funções async (não exigem dados, só não quebram)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bi_io_eh_vazio_sem_dados() -> None:
    """bi_eh_vazio retorna True se não há remanejamentos no período."""
    from app.core.database import session_scope

    async with session_scope() as db:
        vazio = await bi_service.bi_eh_vazio(db, periodo_dias=7)
        # Se houver dados seed, retorna False; se vazio, True. Não assert
        # valor absoluto — só garante que não quebra.
        assert isinstance(vazio, bool)


@pytest.mark.asyncio
async def test_bi_io_calcular_kpis_nao_quebra() -> None:
    """bi_calcular_kpis retorna dict completo (campos esperados)."""
    from app.core.database import session_scope

    async with session_scope() as db:
        kpis = await bi_service.bi_calcular_kpis(db, periodo_dias=7)
        assert "comparecimento" in kpis
        assert "folha_paga" in kpis
        assert "causa_principal_falta" in kpis
        assert "percentual_nack" in kpis
        assert "periodo_inicio" in kpis
        assert "periodo_fim" in kpis
        assert "gerado_em" in kpis


# ---------------------------------------------------------------------------
# 12. API live — RBAC + endpoints (smoke)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bi_api_kpis_sem_auth_retorna_401(client) -> None:
    """GET /bi/kpis sem token → 401."""
    resp = await client.get("/api/v1/bi/kpis")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_bi_api_kpis_fiscal_retorna_403(client, api_token_manoel) -> None:
    """GET /bi/kpis como FISCAL (Manoel) → 403 ROLE_REQUIRED."""
    resp = await client.get(
        "/api/v1/bi/kpis",
        headers={"Authorization": f"Bearer {api_token_manoel}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ROLE_REQUIRED"


@pytest.mark.asyncio
async def test_bi_api_kpis_dirigente_retorna_200(client, api_token_paulo) -> None:
    """GET /bi/kpis como DIRIGENTE (Paulo) → 200 + 4 KPIs."""
    resp = await client.get(
        "/api/v1/bi/kpis?periodo_dias=30",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "comparecimento" in body
    assert "folha_paga" in body
    assert "causa_principal_falta" in body
    assert "percentual_nack" in body


@pytest.mark.asyncio
async def test_bi_api_por_dia_dirigente(client, api_token_paulo) -> None:
    """GET /bi/remanejamentos-por-dia → 200 + série."""
    resp = await client.get(
        "/api/v1/bi/remanejamentos-por-dia?periodo_dias=7",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    # 7 dias → 7 itens.
    assert len(body["items"]) == 7


@pytest.mark.asyncio
async def test_bi_api_drilldown_data_valida(client, api_token_paulo) -> None:
    """GET /bi/remanejamentos-por-dia/{data} → 200 + items."""
    # Usar uma data que sabemos ter dados (do seed).
    resp = await client.get(
        "/api/v1/bi/remanejamentos-por-dia/2026-09-01",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"] == "2026-09-01"
    assert "items" in body
    assert body["total"] >= 0


@pytest.mark.asyncio
async def test_bi_api_insights_dirigente(client, api_token_paulo) -> None:
    """GET /bi/insights → 200 + items."""
    resp = await client.get(
        "/api/v1/bi/insights?periodo_dias=30",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    # Pode ser [] se não há dados suficientes — só checa formato.
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_bi_api_periodo_invalido_retorna_400(client, api_token_paulo) -> None:
    """GET /bi/kpis?periodo_dias=15 → 400 BAD_PERIODO."""
    resp = await client.get(
        "/api/v1/bi/kpis?periodo_dias=15",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "BAD_PERIODO"
