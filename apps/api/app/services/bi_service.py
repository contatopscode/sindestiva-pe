"""SINDESTIVA-PE · BI & Dashboards (Sprint 7 — T7-01..T7-09).

Funções puras (testáveis sem DB) + funções I/O (com DB + cache Redis).

Convenções:
  - Toda função pura recebe listas/dicts e retorna estrutura
    serializável. Sem side effects, sem datetime.now() implícito
    (recebe `agora` como parâmetro pra testabilidade).
  - Funções I/O vivem no final do módulo, com prefixo `bi_*`.
  - Cache Redis opcional (não bloqueia se Redis offline — degradação
    graciosa pra dev/test).

Decisão D-BI-1: KPI "folha paga" usa proxy
`total_remanejamentos × VALOR_HORA_DEFAULT × 8h`. Não temos integração
com folha real no MVP; quando entrar (Fase 3), trocamos pelo cálculo
real. Marcamos como proxy no schema.

Decisão D-BI-2: Insights = regras determinísticas
(remanejamentos ≥ 5 / motivo com mais de 30% / NACK > 10%).
Sem LLM — auditoria exige reprodutibilidade.
"""
from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models import (
    LousaAlocacao,
    MotivoRemanejamentoEnum,
    Porto,
    Remanejamento,
    StatusRemanejamentoEnum,
    Tpa,
    TpaConfirmacaoPresenca,
    Turno,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Proxy de valor-hora (Fase 1 — substituir por integração real).
VALOR_HORA_DEFAULT: float = 25.0
HORAS_POR_REMANEJAMENTO: int = 8

# Janela de dias suportada (espelha Literal[7,30,90,365]).
PERIODOS_VALIDOS: tuple[int, ...] = (7, 30, 90, 365)

# Threshold pra insight de "TPA remanejado 5+ vezes no período" (T7-05).
THRESHOLD_TPA_REMANEJADO: int = 5

# Threshold pra insight de "NACK > 10%" (alerta amarelo).
THRESHOLD_NACK_PCT: float = 10.0

# Threshold pra insight de "motivo > 30% do total".
THRESHOLD_MOTIVO_PCT: float = 30.0

# Top-N (T7-04 = top 10).
TOP_N_REMANEJADOS: int = 10

# Cache TTL (5 min — T7-08).
CACHE_TTL_SEGUNDOS: int = 300


# ---------------------------------------------------------------------------
# Tipos de domínio
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Periodo:
    """Janela [inicio, fim] (inclusivo)."""

    inicio: date
    fim: date

    @classmethod
    def ultimos_dias(cls, dias: int, ref: date | None = None) -> "Periodo":
        """Últimos N dias, terminando em `ref` (ou hoje, em UTC)."""
        if dias not in PERIODOS_VALIDOS:
            raise ValueError(
                f"periodo_dias={dias} não suportado. Use um de {PERIODOS_VALIDOS}."
            )
        fim = ref or datetime.now(tz=timezone.utc).date()
        # `inicio` = `fim - (dias - 1)` (inclusivo: 7 dias = hoje + 6 anteriores).
        inicio = fim - timedelta(days=dias - 1)
        return cls(inicio=inicio, fim=fim)

    def to_dict(self) -> dict[str, str]:
        return {"inicio": self.inicio.isoformat(), "fim": self.fim.isoformat()}


@dataclass(frozen=True)
class RemanejamentoResumo:
    """Subset de `Remanejamento` que as funções puras consomem."""

    id: UUID
    codigo_se: str
    data_referencia: date
    tpa_out_id: UUID
    tpa_out_nome: str
    tpa_out_matricula: str | None
    funcao_origem_id: UUID
    funcao_origem_nome: str
    cais_origem: str | None
    turno_id: UUID
    turno_codigo: str
    motivo: str
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Funções puras (NÃO tocam DB — testáveis com dicts)
# ---------------------------------------------------------------------------


def calcular_comparecimento(
    *,
    total_escalados: int,
    total_confirmados: int,
) -> dict[str, Any]:
    """KPI 1: comparecimento (%)."""
    if total_escalados < 0 or total_confirmados < 0:
        raise ValueError("totais não podem ser negativos")
    if total_confirmados > total_escalados:
        # Defesa em profundidade — pode acontecer se TPAs confirmarem
        # para datas futuras. Cap em escalados.
        total_confirmados = total_escalados
    percentual = (
        round((total_confirmados / total_escalados) * 100, 2)
        if total_escalados > 0
        else 0.0
    )
    return {
        "total_escalados": total_escalados,
        "total_confirmados": total_confirmados,
        "total_ausentes": max(0, total_escalados - total_confirmados),
        "percentual": percentual,
    }


def calcular_folha_paga(
    *,
    total_remanejamentos: int,
    periodo: Periodo,
    valor_hora: float = VALOR_HORA_DEFAULT,
    horas_por_remanejamento: int = HORAS_POR_REMANEJAMENTO,
) -> dict[str, Any]:
    """KPI 2: folha paga em R$ (proxy via count × valor_hora × horas)."""
    if total_remanejamentos < 0:
        raise ValueError("total_remanejamentos não pode ser negativo")
    if valor_hora < 0 or horas_por_remanejamento < 0:
        raise ValueError("valor_hora/horas devem ser ≥ 0")
    valor_total = total_remanejamentos * valor_hora * horas_por_remanejamento
    valor_medio = valor_hora * horas_por_remanejamento
    return {
        "valor_total_brl": round(valor_total, 2),
        "total_remanejamentos": total_remanejamentos,
        "valor_medio_remanejamento_brl": round(valor_medio, 2),
        "periodo_inicio": periodo.inicio,
        "periodo_fim": periodo.fim,
    }


def calcular_causa_principal(
    motivos: Iterable[str],
) -> dict[str, Any]:
    """KPI 3: motivo com maior frequência.

    Retorna dict com `motivo`, `total`, `percentual`.
    Se lista vazia, retorna OUTRO com 0 (placeholder amigável).
    """
    counts = Counter(motivos)
    if not counts:
        return {
            "motivo": MotivoRemanejamentoEnum.OUTRO.value,
            "total": 0,
            "percentual": 0.0,
        }
    total = sum(counts.values())
    motivo, qtde = counts.most_common(1)[0]
    return {
        "motivo": motivo,
        "total": qtde,
        "percentual": round((qtde / total) * 100, 2) if total > 0 else 0.0,
    }


def calcular_percentual_nack(
    *,
    total_notificados: int,
    total_nack: int,
) -> dict[str, Any]:
    """KPI 4: % de NACK (rejeições OGMO) sobre total de notificações."""
    if total_notificados < 0 or total_nack < 0:
        raise ValueError("totais não podem ser negativos")
    if total_nack > total_notificados:
        total_nack = total_notificados
    percentual = (
        round((total_nack / total_notificados) * 100, 2)
        if total_notificados > 0
        else 0.0
    )
    return {
        "total_notificados": total_notificados,
        "total_nack": total_nack,
        "percentual": percentual,
    }


def agrupar_remanejamentos_por_dia(
    remanejamentos: Iterable[RemanejamentoResumo],
    *,
    periodo: Periodo,
) -> dict[str, Any]:
    """T7-02: série temporal (preenche buracos com zero)."""
    counts: dict[date, int] = {}
    for r in remanejamentos:
        if periodo.inicio <= r.data_referencia <= periodo.fim:
            counts[r.data_referencia] = counts.get(r.data_referencia, 0) + 1

    # Preenche dias sem dados (importante pro gráfico não "pular" dias).
    items: list[dict[str, Any]] = []
    dia = periodo.inicio
    total = 0
    while dia <= periodo.fim:
        qtde = counts.get(dia, 0)
        items.append({"data": dia, "total": qtde})
        total += qtde
        dia += timedelta(days=1)

    dias_preenchidos = (periodo.fim - periodo.inicio).days + 1
    media = round(total / dias_preenchidos, 2) if dias_preenchidos > 0 else 0.0
    return {
        "periodo_inicio": periodo.inicio,
        "periodo_fim": periodo.fim,
        "items": items,
        "total": total,
        "media_diaria": media,
    }


def top_remanejados(
    remanejamentos: Iterable[RemanejamentoResumo],
    *,
    n: int = TOP_N_REMANEJADOS,
) -> list[dict[str, Any]]:
    """T7-04: ranking top-N TPAs mais remanejados."""
    counts: dict[UUID, dict[str, Any]] = {}
    for r in remanejamentos:
        entry = counts.setdefault(
            r.tpa_out_id,
            {
                "tpa_id": str(r.tpa_out_id),
                "tpa_nome": r.tpa_out_nome,
                "tpa_matricula": r.tpa_out_matricula,
                "total_remanejamentos": 0,
            },
        )
        entry["total_remanejamentos"] += 1
    ranking = sorted(
        counts.values(), key=lambda x: x["total_remanejamentos"], reverse=True
    )
    return ranking[:n]


def top_funcao_remanejada(
    remanejamentos: Iterable[RemanejamentoResumo],
) -> dict[str, Any] | None:
    """T7-03 card 1: função com + remanejamentos."""
    counts: Counter[str] = Counter(r.funcao_origem_nome for r in remanejamentos)
    return _top_card_from_counter(counts, label_key="funcao")


def top_cais_problematico(
    remanejamentos: Iterable[RemanejamentoResumo],
) -> dict[str, Any] | None:
    """T7-03 card 2: cais com + remanejamentos (ignora NULL)."""
    counts: Counter[str] = Counter(
        r.cais_origem for r in remanejamentos if r.cais_origem
    )
    return _top_card_from_counter(counts, label_key="cais")


def top_horario_critico(
    remanejamentos: Iterable[RemanejamentoResumo],
) -> dict[str, Any] | None:
    """T7-03 card 3: turno com + remanejamentos."""
    counts: Counter[str] = Counter(r.turno_codigo for r in remanejamentos)
    return _top_card_from_counter(counts, label_key="turno")


def _top_card_from_counter(
    counts: Counter[str],
    *,
    label_key: str,  # só pra debug — não vai pro output
) -> dict[str, Any] | None:
    """Helper: converte Counter em top-card com %."""
    if not counts:
        return None
    total = sum(counts.values())
    label, qtde = counts.most_common(1)[0]
    return {
        "label": label,
        "total": qtde,
        "percentual": round((qtde / total) * 100, 2) if total > 0 else 0.0,
    }


def gerar_insights(
    remanejamentos: Iterable[RemanejamentoResumo],
    *,
    periodo: Periodo,
    top_n: int = TOP_N_REMANEJADOS,
) -> list[dict[str, Any]]:
    """T7-05: insights determinísticos (3 regras)."""
    items: list[RemanejamentoResumo] = list(remanejamentos)
    insights: list[dict[str, Any]] = []

    # Regra 1: TPA remanejado 5+ vezes → box amarelo.
    ranking = top_remanejados(items, n=top_n)
    for entry in ranking:
        if entry["total_remanejamentos"] >= THRESHOLD_TPA_REMANEJADO:
            insights.append(
                {
                    "severidade": "alerta",
                    "regra": "TPA_REMANEJADO_5_VEZES",
                    "mensagem": (
                        f"TPA {entry['tpa_nome']} remanejado(a) "
                        f"{entry['total_remanejamentos']}× no período — "
                        "avaliar sobrecarga ou padrão operacional."
                    ),
                    "tpa_id": entry["tpa_id"],
                    "tpa_nome": entry["tpa_nome"],
                    "total": entry["total_remanejamentos"],
                }
            )

    # Regra 2: motivo com > 30% do total → alerta concentrado.
    motivos = [r.motivo for r in items]
    causa = calcular_causa_principal(motivos)
    if causa["total"] > 0 and causa["percentual"] > THRESHOLD_MOTIVO_PCT:
        insights.append(
            {
                "severidade": "alerta",
                "regra": "MOTIVO_CONCENTRADO",
                "mensagem": (
                    f"Motivo '{causa['motivo']}' representa "
                    f"{causa['percentual']}% dos remanejamentos — "
                    "considerar ação preventiva."
                ),
                "total": causa["total"],
            }
        )

    # Regra 3: pico de remanejamentos no dia (≥ 3× a média diária).
    serie = agrupar_remanejamentos_por_dia(items, periodo=periodo)
    media = serie["media_diaria"]
    if media > 0:
        for item in serie["items"]:
            if item["total"] >= max(3, media * 3):
                insights.append(
                    {
                        "severidade": "info",
                        "regra": "PICO_DIA",
                        "mensagem": (
                            f"Pico de {item['total']} remanejamentos em "
                            f"{item['data'].isoformat()} "
                            f"(média do período: {media}/dia)."
                        ),
                    }
                )
                # Só 1 pico (não floodar).
                break

    return insights


# ---------------------------------------------------------------------------
# Cache (Redis opcional — degrada gracioso se offline)
# ---------------------------------------------------------------------------


class _BICache:
    """Wrapper minimalista de cache Redis pra BI (T7-08)."""

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def get_client(self) -> aioredis.Redis | None:
        if self._client is not None:
            return self._client
        try:
            client = aioredis.from_url(  # type: ignore[no-untyped-call]
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=1,
            )
            await client.ping()
            self._client = client
            return client
        except Exception as e:  # noqa: BLE001 — Redis offline é esperado em dev
            log.warning("bi.cache_redis_offline", error=str(e))
            self._client = None
            return None

    async def get(self, key: str) -> dict[str, Any] | None:
        client = await self.get_client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
        except Exception as e:  # noqa: BLE001
            log.warning("bi.cache_get_error", key=key, error=str(e))
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, key: str, value: dict[str, Any], ttl: int = CACHE_TTL_SEGUNDOS) -> None:
        client = await self.get_client()
        if client is None:
            return
        try:
            await client.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception as e:  # noqa: BLE001
            log.warning("bi.cache_set_error", key=key, error=str(e))

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:  # noqa: BLE001
                pass
            self._client = None


_cache = _BICache()


def _cache_key(rotina: str, params: dict[str, Any]) -> str:
    """Chave estável pra cache (params ordenados)."""
    return f"bi:{rotina}:{json.dumps(params, sort_keys=True, default=str)}"


# ---------------------------------------------------------------------------
# I/O — DB queries
# ---------------------------------------------------------------------------


async def _buscar_remanejamentos_periodo(
    db: AsyncSession,
    *,
    periodo: Periodo,
) -> list[RemanejamentoResumo]:
    """Busca remanejamentos do período + já normaliza pra dataclass."""
    # JOIN com Tpa (tpa_out) + Funcao + Turno.
    stmt = (
        select(
            Remanejamento.id,
            Remanejamento.codigo_se,
            Remanejamento.data_referencia,
            Remanejamento.tpa_out_id,
            Tpa.nome_completo.label("tpa_out_nome"),
            Tpa.matricula_ogmo.label("tpa_out_matricula"),
            Remanejamento.funcao_origem_id,
            # Funcao.nome_exibicao — joinedload evita N+1.
            Remanejamento.cais_origem,
            Remanejamento.turno_id,
            Turno.codigo.label("turno_codigo"),
            Remanejamento.motivo,
            Remanejamento.status,
            Remanejamento.created_at,
        )
        .join(Tpa, Tpa.id == Remanejamento.tpa_out_id)
        .join(Turno, Turno.id == Remanejamento.turno_id)
        .where(Remanejamento.data_referencia >= periodo.inicio)
        .where(Remanejamento.data_referencia <= periodo.fim)
        .where(Remanejamento.deleted_at.is_(None))
        .order_by(Remanejamento.data_referencia, Remanejamento.created_at)
    )
    # Import tardio pra evitar ciclo: Funcao está em catalogos.
    from app.models import Funcao  # noqa: PLC0415

    stmt = stmt.add_columns(Funcao.nome_exibicao.label("funcao_origem_nome")).join(
        Funcao, Funcao.id == Remanejamento.funcao_origem_id
    )

    rows = (await db.execute(stmt)).all()
    return [
        RemanejamentoResumo(
            id=row.id,
            codigo_se=row.codigo_se,
            data_referencia=row.data_referencia,
            tpa_out_id=row.tpa_out_id,
            tpa_out_nome=row.tpa_out_nome,
            tpa_out_matricula=row.tpa_out_matricula,
            funcao_origem_id=row.funcao_origem_id,
            funcao_origem_nome=row.funcao_origem_nome,
            cais_origem=row.cais_origem,
            turno_id=row.turno_id,
            turno_codigo=row.turno_codigo,
            motivo=row.motivo.value if hasattr(row.motivo, "value") else str(row.motivo),
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            created_at=row.created_at,
        )
        for row in rows
    ]


async def _contar_confirmacoes_presenca(
    db: AsyncSession,
    *,
    periodo: Periodo,
) -> tuple[int, int]:
    """Retorna (total_escalados, total_confirmados) no período.

    `total_escalados` = count de LousaAlocacao com `trabalhador_id`
    (conciliação feita) — ou seja, alocações reconciliadas. Quando
    a reconciliação batch não rodou ainda, alocação tem só
    `trabalhador_matricula` (chave funcional) e `trabalhador_id=NULL`
    — não contamos, pra não inflar o denominador.

    `total_confirmados` = count de TpaConfirmacaoPresenca.confirmou=True
    no período.
    """
    escalados_q = (
        select(LousaAlocacao)
        .where(LousaAlocacao.data_referencia >= periodo.inicio)
        .where(LousaAlocacao.data_referencia <= periodo.fim)
        .where(LousaAlocacao.trabalhador_id.is_not(None))
    )
    escalados = len((await db.execute(escalados_q)).all())

    confirmados_q = (
        select(TpaConfirmacaoPresenca)
        .where(TpaConfirmacaoPresenca.data_referencia >= periodo.inicio)
        .where(TpaConfirmacaoPresenca.data_referencia <= periodo.fim)
        .where(TpaConfirmacaoPresenca.confirmou.is_(True))
        .where(TpaConfirmacaoPresenca.deleted_at.is_(None))
    )
    confirmados = len((await db.execute(confirmados_q)).all())
    return escalados, confirmados


async def _contar_nacks(db: AsyncSession, *, periodo: Periodo) -> tuple[int, int]:
    """Retorna (total_notificados, total_nack) no período.

    `total_notificados` = count de Remanejamento com status >= NOTIFICADO_OGMO
    (ou seja, que virou e-mail pro OGMO). `total_nack` = count com
    status=NACK. O status CANCELADO não conta (não foi rejeitado, foi cancelado).
    """
    notificados_q = (
        select(Remanejamento)
        .where(Remanejamento.data_referencia >= periodo.inicio)
        .where(Remanejamento.data_referencia <= periodo.fim)
        .where(Remanejamento.deleted_at.is_(None))
        .where(
            Remanejamento.status.in_(
                [
                    StatusRemanejamentoEnum.NOTIFICADO_OGMO,
                    StatusRemanejamentoEnum.ACK,
                    StatusRemanejamentoEnum.NACK,
                ]
            )
        )
    )
    notificados = len((await db.execute(notificados_q)).all())

    nack_q = notificados_q.where(
        Remanejamento.status == StatusRemanejamentoEnum.NACK
    )
    nack = len((await db.execute(nack_q)).all())
    return notificados, nack


# ---------------------------------------------------------------------------
# Endpoints "de borda" (compõem cache + funções puras + I/O)
# ---------------------------------------------------------------------------


async def bi_calcular_kpis(
    db: AsyncSession,
    *,
    periodo_dias: int = 30,
) -> dict[str, Any]:
    """Compoe os 4 KPIs (T7-01)."""
    periodo = Periodo.ultimos_dias(periodo_dias)
    cache_k = _cache_key(
        "kpis", {"periodo_dias": periodo_dias, **periodo.to_dict()}
    )
    cached = await _cache.get(cache_k)
    if cached is not None:
        cached["gerado_em"] = datetime.now(tz=timezone.utc)
        return cached

    # I/O
    rems = await _buscar_remanejamentos_periodo(db, periodo=periodo)
    escalados, confirmados = await _contar_confirmacoes_presenca(db, periodo=periodo)
    notificados, nack = await _contar_nacks(db, periodo=periodo)

    # Puro
    comparecimento = calcular_comparecimento(
        total_escalados=escalados, total_confirmados=confirmados
    )
    folha = calcular_folha_paga(
        total_remanejamentos=len(rems), periodo=periodo
    )
    causa = calcular_causa_principal([r.motivo for r in rems])
    nack_kpi = calcular_percentual_nack(
        total_notificados=notificados, total_nack=nack
    )

    payload = {
        "periodo_inicio": periodo.inicio,
        "periodo_fim": periodo.fim,
        "comparecimento": comparecimento,
        "folha_paga": folha,
        "causa_principal_falta": causa,
        "percentual_nack": nack_kpi,
        "gerado_em": datetime.now(tz=timezone.utc),
    }
    # Cache: serializa date/datetime pra JSON.
    await _cache.set(cache_k, _json_safe(payload))
    return payload


async def bi_remanejamentos_por_dia(
    db: AsyncSession,
    *,
    periodo_dias: int = 30,
) -> dict[str, Any]:
    """T7-02: série temporal."""
    periodo = Periodo.ultimos_dias(periodo_dias)
    cache_k = _cache_key(
        "por-dia", {"periodo_dias": periodo_dias, **periodo.to_dict()}
    )
    cached = await _cache.get(cache_k)
    if cached is not None:
        return cached

    rems = await _buscar_remanejamentos_periodo(db, periodo=periodo)
    payload = agrupar_remanejamentos_por_dia(rems, periodo=periodo)
    await _cache.set(cache_k, _json_safe(payload))
    return payload


async def bi_top_remanejados(
    db: AsyncSession,
    *,
    periodo_dias: int = 30,
    n: int = TOP_N_REMANEJADOS,
) -> dict[str, Any]:
    """T7-04: ranking top-N."""
    periodo = Periodo.ultimos_dias(periodo_dias)
    cache_k = _cache_key(
        "top",
        {"periodo_dias": periodo_dias, "n": n, **periodo.to_dict()},
    )
    cached = await _cache.get(cache_k)
    if cached is not None:
        return cached

    rems = await _buscar_remanejamentos_periodo(db, periodo=periodo)
    ranking = top_remanejados(rems, n=n)
    payload = {
        "periodo_inicio": periodo.inicio,
        "periodo_fim": periodo.fim,
        "items": ranking,
    }
    await _cache.set(cache_k, _json_safe(payload))
    return payload


async def bi_top_cards(
    db: AsyncSession,
    *,
    periodo_dias: int = 30,
) -> dict[str, Any]:
    """T7-03: 3 cards top-1 (função / cais / horário)."""
    periodo = Periodo.ultimos_dias(periodo_dias)
    cache_k = _cache_key(
        "cards", {"periodo_dias": periodo_dias, **periodo.to_dict()}
    )
    cached = await _cache.get(cache_k)
    if cached is not None:
        return cached

    rems = await _buscar_remanejamentos_periodo(db, periodo=periodo)
    payload = {
        "funcao_mais_remanejada": top_funcao_remanejada(rems),
        "cais_mais_problematico": top_cais_problematico(rems),
        "horario_mais_critico": top_horario_critico(rems),
    }
    await _cache.set(cache_k, _json_safe(payload))
    return payload


async def bi_insights(
    db: AsyncSession,
    *,
    periodo_dias: int = 30,
) -> dict[str, Any]:
    """T7-05: insights automáticos."""
    periodo = Periodo.ultimos_dias(periodo_dias)
    cache_k = _cache_key(
        "insights", {"periodo_dias": periodo_dias, **periodo.to_dict()}
    )
    cached = await _cache.get(cache_k)
    if cached is not None:
        return cached

    rems = await _buscar_remanejamentos_periodo(db, periodo=periodo)
    items = gerar_insights(rems, periodo=periodo)
    payload = {
        "periodo_inicio": periodo.inicio,
        "periodo_fim": periodo.fim,
        "items": items,
    }
    await _cache.set(cache_k, _json_safe(payload))
    return payload


async def bi_drilldown_dia(
    db: AsyncSession,
    *,
    data: date,
) -> dict[str, Any]:
    """T7-06: drill-down de 1 dia (clicar em barra)."""
    # Sem cache aqui — drill-down é chamado sob demanda, dados mudam.
    from app.models import Funcao, Tpa  # noqa: PLC0415

    stmt = (
        select(
            Remanejamento.id,
            Remanejamento.codigo_se,
            Remanejamento.motivo,
            Remanejamento.status,
            Remanejamento.data_referencia,
            Remanejamento.created_at,
            Tpa.nome_completo.label("tpa_out_nome"),
        )
        .join(Tpa, Tpa.id == Remanejamento.tpa_out_id)
        .where(Remanejamento.data_referencia == data)
        .where(Remanejamento.deleted_at.is_(None))
        .order_by(Remanejamento.created_at)
    )
    stmt = stmt.add_columns(Funcao.nome_exibicao.label("_dummy")).join(
        Funcao, Funcao.id == Remanejamento.funcao_origem_id
    )
    rows = (await db.execute(stmt)).all()

    items = [
        {
            "id": str(r.id),
            "codigo_se": r.codigo_se,
            "tpa_out_nome": r.tpa_out_nome,
            "tpa_in_nome": None,  # poderia buscar, mas simplificado
            "motivo": r.motivo.value if hasattr(r.motivo, "value") else str(r.motivo),
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "data_referencia": r.data_referencia,
            "hora_criacao": r.created_at,
        }
        for r in rows
    ]
    return {"data": data, "items": items, "total": len(items)}


async def bi_eh_vazio(
    db: AsyncSession,
    *,
    periodo_dias: int = 30,
) -> bool:
    """T7-12: True se não há dados no período (pra empty state)."""
    periodo = Periodo.ultimos_dias(periodo_dias)
    rems = await _buscar_remanejamentos_periodo(db, periodo=periodo)
    return len(rems) == 0


def _json_safe(value: Any) -> Any:
    """Converte date/datetime pra string (recursivo)."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


# Reexport pra cleanup no shutdown.
__all__ = [
    # Constantes
    "VALOR_HORA_DEFAULT",
    "HORAS_POR_REMANEJAMENTO",
    "PERIODOS_VALIDOS",
    "THRESHOLD_TPA_REMANEJADO",
    "THRESHOLD_NACK_PCT",
    "THRESHOLD_MOTIVO_PCT",
    "TOP_N_REMANEJADOS",
    "CACHE_TTL_SEGUNDOS",
    # Tipos
    "Periodo",
    "RemanejamentoResumo",
    # Funções puras
    "calcular_comparecimento",
    "calcular_folha_paga",
    "calcular_causa_principal",
    "calcular_percentual_nack",
    "agrupar_remanejamentos_por_dia",
    "top_remanejados",
    "top_funcao_remanejada",
    "top_cais_problematico",
    "top_horario_critico",
    "gerar_insights",
    # I/O
    "bi_calcular_kpis",
    "bi_remanejamentos_por_dia",
    "bi_top_remanejados",
    "bi_top_cards",
    "bi_insights",
    "bi_drilldown_dia",
    "bi_eh_vazio",
]
