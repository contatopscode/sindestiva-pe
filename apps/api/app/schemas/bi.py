"""SINDESTIVA-PE · Pydantic schemas — BI & Dashboards (Sprint 7).

Modelo de dados pra alimentar o dashboard do Presidente (Josias).
KPIs:
  - comparecimento  (TPA que confirmou presença via PWA)
  - folha_paga      (proxy: count de remanejamentos × valor_estimado)
  - causa_principal_falta (motivo com maior frequência)
  - percentual_nack (status=NACK / status NOTIFICADO_OGMO)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

# Janela de análise pré-definida (T7-02: filtro 7/30/90/365 dias).
PeriodoDias = Literal[7, 30, 90, 365]


class BIQueryParams(BaseModel):
    """Query params comuns aos endpoints de BI."""

    periodo_dias: PeriodoDias = Field(
        default=30,
        description="Janela de análise em dias (7/30/90/365).",
    )


# ---------------------------------------------------------------------------
# KPIs (T7-01)
# ---------------------------------------------------------------------------


class KpiComparecimento(BaseModel):
    """TPA escalados vs TPA que confirmaram presença via PWA."""

    total_escalados: int = Field(ge=0)
    total_confirmados: int = Field(ge=0)
    total_ausentes: int = Field(ge=0)
    percentual: float = Field(ge=0.0, le=100.0)


class KpiFolhaPaga(BaseModel):
    """Folha paga em R$ (proxy: count de remanejamentos × valor_estimado).

    Quando o sistema tiver integração com folha real (Fase 3), troca
    o cálculo. Por enquanto usa o número de TPA-hora × valor médio
    da categoria (R$ 25/hora default, configurável em env).
    """

    valor_total_brl: float = Field(ge=0.0)
    total_remanejamentos: int = Field(ge=0)
    valor_medio_remanejamento_brl: float = Field(ge=0.0)
    periodo_inicio: date
    periodo_fim: date


class KpiCausaPrincipal(BaseModel):
    """Motivo de remanejamento com maior frequência no período."""

    motivo: str
    total: int = Field(ge=0)
    percentual: float = Field(ge=0.0, le=100.0)


class KpiPercentualNack(BaseModel):
    """% de notificações OGMO rejeitadas (NACK)."""

    total_notificados: int = Field(ge=0)
    total_nack: int = Field(ge=0)
    percentual: float = Field(ge=0.0, le=100.0)


class BIKpisResponse(BaseModel):
    """4 KPIs da tela /bi (T7-01)."""

    periodo_inicio: date
    periodo_fim: date
    comparecimento: KpiComparecimento
    folha_paga: KpiFolhaPaga
    causa_principal_falta: KpiCausaPrincipal
    percentual_nack: KpiPercentualNack
    gerado_em: datetime


# ---------------------------------------------------------------------------
# Série temporal (T7-02)
# ---------------------------------------------------------------------------


class RemanejamentosPorDiaItem(BaseModel):
    """1 dia da série."""

    data: date
    total: int = Field(ge=0)


class RemanejamentosPorDiaResponse(BaseModel):
    """Série temporal: count de remanejamentos por dia (T7-02)."""

    periodo_inicio: date
    periodo_fim: date
    items: list[RemanejamentosPorDiaItem]
    total: int = Field(ge=0)
    media_diaria: float = Field(ge=0.0)


# ---------------------------------------------------------------------------
# Top remanejados (T7-04)
# ---------------------------------------------------------------------------


class TopRemanejadoItem(BaseModel):
    """1 TPA no ranking."""

    tpa_id: str
    tpa_nome: str
    tpa_matricula: str | None
    total_remanejamentos: int = Field(ge=0)


class TopRemanejadosResponse(BaseModel):
    """Ranking top-N TPAs mais remanejados (T7-04)."""

    periodo_inicio: date
    periodo_fim: date
    items: list[TopRemanejadoItem]


# ---------------------------------------------------------------------------
# Cards "Top-1" (T7-03)
# ---------------------------------------------------------------------------


class TopCardItem(BaseModel):
    """Card 'top-1' (Função + remanejada / Cais + problemático / Horário + crítico)."""

    label: str  # ex.: "CONFERENTE"
    total: int = Field(ge=0)
    percentual: float = Field(ge=0.0, le=100.0)


class TopCardsResponse(BaseModel):
    """3 cards top-1 (T7-03)."""

    funcao_mais_remanejada: TopCardItem | None
    cais_mais_problematico: TopCardItem | None
    horario_mais_critico: TopCardItem | None


# ---------------------------------------------------------------------------
# Insights (T7-05)
# ---------------------------------------------------------------------------


class InsightItem(BaseModel):
    """Insight automático (regra: TPA remanejado 5+ vezes no período)."""

    severidade: Literal["info", "alerta", "critico"]
    regra: str
    mensagem: str
    tpa_id: str | None = None
    tpa_nome: str | None = None
    total: int | None = None


class InsightsResponse(BaseModel):
    """Lista de insights (T7-05)."""

    periodo_inicio: date
    periodo_fim: date
    items: list[InsightItem]


# ---------------------------------------------------------------------------
# Drill-down (T7-06)
# ---------------------------------------------------------------------------


class DrillDownItem(BaseModel):
    """Detalhe dos remanejamentos de 1 dia (T7-06)."""

    id: str
    codigo_se: str
    tpa_out_nome: str
    tpa_in_nome: str | None
    motivo: str
    status: str
    data_referencia: date
    hora_criacao: datetime


class DrillDownResponse(BaseModel):
    """Drill-down de 1 dia da série (T7-06)."""

    data: date
    items: list[DrillDownItem]
    total: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Empty state (T7-12)
# ---------------------------------------------------------------------------


class BIEmptyResponse(BaseModel):
    """Resposta vazia (T7-12) — quando não há dados no período."""

    periodo_inicio: date
    periodo_fim: date
    vazio: bool = True
    mensagem: str = "Sem dados no período selecionado."


__all__ = [
    "BIQueryParams",
    "BIKpisResponse",
    "KpiComparecimento",
    "KpiFolhaPaga",
    "KpiCausaPrincipal",
    "KpiPercentualNack",
    "RemanejamentosPorDiaResponse",
    "RemanejamentosPorDiaItem",
    "TopRemanejadosResponse",
    "TopRemanejadoItem",
    "TopCardsResponse",
    "TopCardItem",
    "InsightsResponse",
    "InsightItem",
    "DrillDownResponse",
    "DrillDownItem",
    "BIEmptyResponse",
]
