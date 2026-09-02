"""SINDESTIVA-PE · /bi (BI & Dashboards — Sprint 7).

Endpoints (todos com cache Redis 5min + role DIRIGENTE):
  GET /bi/kpis                          → 4 KPIs (T7-01)
  GET /bi/remanejamentos-por-dia        → série temporal (T7-02)
  GET /bi/remanejamentos-por-dia/{data} → drill-down (T7-06)
  GET /bi/top-remanejados               → ranking top 10 (T7-04)
  GET /bi/top-cards                     → 3 cards top-1 (T7-03)
  GET /bi/insights                      → insights determinísticos (T7-05)
  GET /bi/export-pdf                    → PDF do BI (T7-07)

Autenticação: DIRIGENTE (Josias/Paulo). Fiscais NÃO veem BI —
dashboards são pra diretoria (CCT, prestação de contas).
"""
from __future__ import annotations

import hashlib
import io
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import get_logger
from app.core.security import get_current_user_id, get_current_user_role, oauth2_scheme
from app.schemas.bi import (
    BIKpisResponse,
    DrillDownResponse,
    InsightsResponse,
    RemanejamentosPorDiaResponse,
    TopCardsResponse,
    TopRemanejadosResponse,
)
from app.services import bi_service

log = get_logger(__name__)

router = APIRouter(prefix="/bi", tags=["bi"])


# ---------------------------------------------------------------------------
# Guard: só DIRIGENTE (Presidente/Diretor) vê BI
# ---------------------------------------------------------------------------


def _require_dirigente(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> str:
    """Garante que o caller é DIRIGENTE. 401 se não autenticado, 403 se errado role."""
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )
    role = get_current_user_role(token=token)
    if role != "DIRIGENTE":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ROLE_REQUIRED",
                "message": f"BI restrito a DIRIGENTE (você é {role}).",
            },
        )
    return user_id


# ---------------------------------------------------------------------------
# 1. KPIs (T7-01)
# ---------------------------------------------------------------------------


@router.get(
    "/kpis",
    response_model=BIKpisResponse,
    summary="4 KPIs do BI (comparecimento, folha paga, causa #1 falta, % NACK)",
)
async def get_kpis(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_require_dirigente)],
    periodo_dias: int = Query(30, description="Janela em dias (7/30/90/365)"),
) -> BIKpisResponse:
    """T7-01: 4 KPIs da tela /bi."""
    try:
        payload = await bi_service.bi_calcular_kpis(db, periodo_dias=periodo_dias)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "BAD_PERIODO", "message": str(e)})
    return BIKpisResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# 2. Série temporal (T7-02)
# ---------------------------------------------------------------------------


@router.get(
    "/remanejamentos-por-dia",
    response_model=RemanejamentosPorDiaResponse,
    summary="Série temporal: remanejamentos por dia (filtro 7/30/90/365)",
)
async def get_remanejamentos_por_dia(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_require_dirigente)],
    periodo_dias: int = Query(30, description="Janela em dias (7/30/90/365)"),
) -> RemanejamentosPorDiaResponse:
    """T7-02: série temporal pro gráfico de barras ECharts."""
    try:
        payload = await bi_service.bi_remanejamentos_por_dia(
            db, periodo_dias=periodo_dias
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "BAD_PERIODO", "message": str(e)})
    return RemanejamentosPorDiaResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# 3. Drill-down (T7-06)
# ---------------------------------------------------------------------------


@router.get(
    "/remanejamentos-por-dia/{data}",
    response_model=DrillDownResponse,
    summary="Drill-down: detalhe dos remanejamentos de 1 dia",
)
async def get_drilldown_dia(
    data: date,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_require_dirigente)],
) -> DrillDownResponse:
    """T7-06: clicar em barra do gráfico abre detalhe do dia."""
    payload = await bi_service.bi_drilldown_dia(db, data=data)
    return DrillDownResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# 4. Top remanejados (T7-04)
# ---------------------------------------------------------------------------


@router.get(
    "/top-remanejados",
    response_model=TopRemanejadosResponse,
    summary="Ranking top 10 TPAs mais remanejados",
)
async def get_top_remanejados(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_require_dirigente)],
    periodo_dias: int = Query(30, description="Janela em dias (7/30/90/365)"),
    n: int = Query(10, ge=1, le=50, description="Tamanho do ranking"),
) -> TopRemanejadosResponse:
    """T7-04: ranking top-N."""
    try:
        payload = await bi_service.bi_top_remanejados(
            db, periodo_dias=periodo_dias, n=n
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "BAD_PERIODO", "message": str(e)})
    return TopRemanejadosResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# 5. Top cards (T7-03)
# ---------------------------------------------------------------------------


@router.get(
    "/top-cards",
    response_model=TopCardsResponse,
    summary="3 cards top-1: função/cais/horário com mais remanejamentos",
)
async def get_top_cards(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_require_dirigente)],
    periodo_dias: int = Query(30, description="Janela em dias (7/30/90/365)"),
) -> TopCardsResponse:
    """T7-03: cards de destaque."""
    try:
        payload = await bi_service.bi_top_cards(db, periodo_dias=periodo_dias)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "BAD_PERIODO", "message": str(e)})
    return TopCardsResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# 6. Insights (T7-05)
# ---------------------------------------------------------------------------


@router.get(
    "/insights",
    response_model=InsightsResponse,
    summary="Insights automáticos (regras determinísticas)",
)
async def get_insights(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_require_dirigente)],
    periodo_dias: int = Query(30, description="Janela em dias (7/30/90/365)"),
) -> InsightsResponse:
    """T7-05: regras (TPA 5×, motivo > 30%, pico diário)."""
    try:
        payload = await bi_service.bi_insights(db, periodo_dias=periodo_dias)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "BAD_PERIODO", "message": str(e)})
    return InsightsResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# 7. Export PDF (T7-07)
# ---------------------------------------------------------------------------


def _render_bi_pdf(
    *,
    kpis: dict[str, Any],
    por_dia: dict[str, Any],
    top: list[dict[str, Any]],
    cards: dict[str, Any],
    insights: list[dict[str, Any]],
    periodo_dias: int,
) -> bytes:
    """Renderiza o BI como PDF (capa + 4 seções) com WeasyPrint.

    Mantém o template INLINE pra não criar mais um arquivo — é só
    uma página de PDF (manual do Presidente T7-10 vai em arquivo
    separado). Usa cores sóbrias (paleta SINDESTIVA: azul-marinho +
    cinza) e tabela com dados.
    """
    from weasyprint import HTML  # type: ignore[import-not-found]

    # Hash do conteúdo (T7-07: prova de integridade).
    content_hash_input = (
        f"{kpis.get('gerado_em')}|{periodo_dias}|"
        f"{sum(i['total'] for i in por_dia['items'])}|"
        f"{sum(i['total_remanejamentos'] for i in top)}"
    ).encode("utf-8")
    content_hash = hashlib.sha256(content_hash_input).hexdigest()[:16]

    # Helpers de formatação.
    def brl(v: Any) -> str:
        try:
            return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
            return "—"

    def pct(v: Any) -> str:
        try:
            return f"{float(v):.1f}%"
        except (TypeError, ValueError):
            return "—"

    # Série temporal (top 14 dias pra caber na página).
    serie_rows = "".join(
        f"<tr><td>{i['data']}</td><td class='num'>{i['total']}</td></tr>"
        for i in por_dia["items"][-14:]
    )

    # Top remanejados.
    top_rows = "".join(
        f"<tr><td>{i['tpa_nome']}</td><td>{i.get('tpa_matricula') or '—'}</td>"
        f"<td class='num'>{i['total_remanejamentos']}</td></tr>"
        for i in top
    )

    # Cards top-1.
    def render_card(label: str, item: dict[str, Any] | None) -> str:
        if item is None:
            return f"<div class='card'><h4>{label}</h4><p class='muted'>Sem dados</p></div>"
        return (
            f"<div class='card'>"
            f"<h4>{label}</h4>"
            f"<p class='big'>{item['label']}</p>"
            f"<p>{item['total']} remanejamentos · {pct(item['percentual'])}</p>"
            f"</div>"
        )

    # Insights.
    insights_html = (
        "".join(
            f"<li class='insight insight-{ins['severidade']}'>"
            f"<strong>[{ins['severidade'].upper()}]</strong> {ins['mensagem']}</li>"
            for ins in insights
        )
        if insights
        else "<li class='muted'>Nenhum insight no período.</li>"
    )

    html_doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>SINDESTIVA-PE · BI — últimos {periodo_dias} dias</title>
<style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: 'Helvetica', 'Arial', sans-serif; font-size: 10pt; color: #1a2540; }}
h1 {{ color: #1a2540; border-bottom: 3px solid #c8a04d; padding-bottom: 6px; }}
h2 {{ color: #1a2540; margin-top: 24px; border-left: 4px solid #c8a04d; padding-left: 8px; }}
.meta {{ color: #6b7280; font-size: 9pt; margin-bottom: 24px; }}
.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
.kpi {{ background: #f3f4f6; padding: 12px; border-left: 3px solid #c8a04d; }}
.kpi .label {{ font-size: 8pt; text-transform: uppercase; color: #6b7280; }}
.kpi .value {{ font-size: 18pt; font-weight: bold; color: #1a2540; margin-top: 4px; }}
.cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }}
.card {{ background: #1a2540; color: white; padding: 12px; }}
.card h4 {{ margin: 0; font-size: 8pt; text-transform: uppercase; color: #c8a04d; }}
.card .big {{ font-size: 14pt; font-weight: bold; margin: 4px 0; }}
.card p {{ margin: 0; font-size: 9pt; }}
.muted {{ color: #6b7280; font-style: italic; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 9pt; }}
th, td {{ padding: 6px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
th {{ background: #1a2540; color: white; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
ul.insights {{ list-style: none; padding: 0; }}
li.insight {{ padding: 8px 12px; margin-bottom: 6px; border-left: 3px solid #c8a04d; background: #fffbeb; }}
li.insight-critico {{ border-color: #dc2626; background: #fef2f2; }}
li.insight-alerta {{ border-color: #d97706; background: #fffbeb; }}
li.insight-info {{ border-color: #2563eb; background: #eff6ff; }}
.hash {{ font-family: monospace; color: #6b7280; font-size: 7pt; margin-top: 24px; text-align: right; }}
footer {{ margin-top: 24px; border-top: 1px solid #e5e7eb; padding-top: 8px; font-size: 8pt; color: #6b7280; }}
</style>
</head>
<body>

<h1>SINDESTIVA-PE · BI — últimos {periodo_dias} dias</h1>
<p class="meta">
Período: {kpis['periodo_inicio']} a {kpis['periodo_fim']} ·
Gerado em: {kpis['gerado_em']} ·
Hash: {content_hash}
</p>

<h2>1. KPIs principais</h2>
<div class="kpis">
  <div class="kpi"><div class="label">Comparecimento</div><div class="value">{pct(kpis['comparecimento']['percentual'])}</div>
    <p class="muted">{kpis['comparecimento']['total_confirmados']}/{kpis['comparecimento']['total_escalados']}</p></div>
  <div class="kpi"><div class="label">Folha paga</div><div class="value">{brl(kpis['folha_paga']['valor_total_brl'])}</div>
    <p class="muted">{kpis['folha_paga']['total_remanejamentos']} remanejamentos</p></div>
  <div class="kpi"><div class="label">Causa #1 falta</div><div class="value">{kpis['causa_principal_falta']['motivo']}</div>
    <p class="muted">{kpis['causa_principal_falta']['total']} ({pct(kpis['causa_principal_falta']['percentual'])})</p></div>
  <div class="kpi"><div class="label">% NACK</div><div class="value">{pct(kpis['percentual_nack']['percentual'])}</div>
    <p class="muted">{kpis['percentual_nack']['total_nack']}/{kpis['percentual_nack']['total_notificados']}</p></div>
</div>

<h2>2. Remanejamentos por dia (últimos 14 dias)</h2>
<table>
  <thead><tr><th>Data</th><th class="num">Total</th></tr></thead>
  <tbody>{serie_rows}</tbody>
</table>

<h2>3. Top remanejados (ranking)</h2>
<table>
  <thead><tr><th>Nome</th><th>Matrícula</th><th class="num">Total</th></tr></thead>
  <tbody>{top_rows or "<tr><td colspan='3' class='muted'>Sem dados no período.</td></tr>"}</tbody>
</table>

<h2>4. Cards de destaque</h2>
<div class="cards">
  {render_card("Função + remanejada", cards.get("funcao_mais_remanejada"))}
  {render_card("Cais + problemático", cards.get("cais_mais_problematico"))}
  {render_card("Horário + crítico", cards.get("horario_mais_critico"))}
</div>

<h2>5. Insights automáticos</h2>
<ul class="insights">{insights_html}</ul>

<footer>
SINDESTIVA-PE · Lousa Digital · SINDESTIVA Bot · Hash de integridade: {content_hash}
</footer>

</body>
</html>"""

    pdf_bytes = HTML(string=html_doc).write_pdf()
    return pdf_bytes


@router.get(
    "/export-pdf",
    summary="Exporta o BI como PDF (T7-07, < 30s)",
    response_class=StreamingResponse,
)
async def export_pdf(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_require_dirigente)],
    periodo_dias: int = Query(30, description="Janela em dias (7/30/90/365)"),
) -> StreamingResponse:
    """T7-07: PDF do BI com capa + 4 seções + hash de integridade."""
    try:
        kpis = await bi_service.bi_calcular_kpis(db, periodo_dias=periodo_dias)
        por_dia = await bi_service.bi_remanejamentos_por_dia(
            db, periodo_dias=periodo_dias
        )
        top = await bi_service.bi_top_remanejados(
            db, periodo_dias=periodo_dias
        )
        cards = await bi_service.bi_top_cards(db, periodo_dias=periodo_dias)
        insights = await bi_service.bi_insights(db, periodo_dias=periodo_dias)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "BAD_PERIODO", "message": str(e)})

    pdf_bytes = _render_bi_pdf(
        kpis=kpis,
        por_dia=por_dia,
        top=top.get("items", []),
        cards=cards,
        insights=insights.get("items", []),
        periodo_dias=periodo_dias,
    )

    filename = f"sindestiva-bi-{periodo_dias}d.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Hash": hashlib.sha256(pdf_bytes).hexdigest()[:16],
        },
    )


__all__ = ["router"]
