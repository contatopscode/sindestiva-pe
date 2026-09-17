// =============================================================================
// SINDESTIVA-PE · /bi — helpers de UI (período, labels, formatação)
// =============================================================================

import type { PeriodoDias } from "@/lib/tipos";

export interface BiPeriodoTab {
  value: PeriodoDias;
  label: string;
}

/** Tabs do protótipo → `periodo_dias` na API. */
export const BI_PERIODOS: BiPeriodoTab[] = [
  { value: 7, label: "7 dias" },
  { value: 30, label: "30 dias" },
  { value: 90, label: "3 meses" },
  { value: 365, label: "12 meses" },
];

export function periodoDiasFromTabValue(value: number): PeriodoDias | null {
  const found = BI_PERIODOS.find((p) => p.value === value);
  return found ? found.value : null;
}

/** Título do gráfico conforme período selecionado. */
export function remanejamentosChartHeading(periodo: PeriodoDias): string {
  switch (periodo) {
    case 7:
      return "REMANEJAMENTOS POR DIA · ÚLTIMOS 7 DIAS";
    case 30:
      return "REMANEJAMENTOS POR DIA · ÚLTIMOS 30 DIAS";
    case 90:
      return "REMANEJAMENTOS POR DIA · ÚLTIMOS 3 MESES";
    case 365:
      return "REMANEJAMENTOS POR DIA · ÚLTIMOS 12 MESES";
    default:
      return "REMANEJAMENTOS POR DIA";
  }
}

/** Badge da coluna TOP REMANEJADOS. */
export function topRemanejadosPeriodBadge(periodo: PeriodoDias): string {
  switch (periodo) {
    case 7:
      return "7 DIAS";
    case 30:
      return "30 DIAS";
    case 90:
      return "3 MESES";
    case 365:
      return "12 MESES";
    default:
      return `${periodo} DIAS`;
  }
}

export function folhaPagaCardDetail(periodo: PeriodoDias, totalTpas: number): string {
  const periodoLabel =
    periodo === 90 ? "3 meses" : periodo === 365 ? "12 meses" : `${periodo}d`;
  const tpas = totalTpas.toLocaleString("pt-BR");
  return `Folha paga ${periodoLabel} · ${tpas} TPAs`;
}

/** Valor compacto estilo protótipo (ex.: R$ 487k). */
export function formatBrlCompact(valor: number): string {
  const abs = Math.abs(valor);
  if (abs >= 1_000_000) {
    const m = valor / 1_000_000;
    const formatted = m >= 10 ? m.toFixed(0) : m.toFixed(1).replace(/\.0$/, "");
    return `R$ ${formatted}M`;
  }
  if (abs >= 1_000) {
    const k = valor / 1_000;
    const formatted = k >= 100 ? k.toFixed(0) : k.toFixed(1).replace(/\.0$/, "");
    return `R$ ${formatted}k`;
  }
  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

export function formatTaxaComparecimento(percentual: number): string {
  return `${Math.round(percentual)}%`;
}

const MOTIVO_BI_LABELS: Record<string, string> = {
  ATESTADO_MEDICO: "Atestado",
  FALTA_INJUSTIFICADA: "Falta injustificada",
  REFORCO_TERNO: "Reforço de terno",
  TROCA_TURNO: "Troca de turno",
  ATRASO_15MIN: "Atraso superior a 15 min",
  FALTA_EPI: "Falta de EPI",
  LIBERACAO_ANTECIPADA: "Liberação antecipada",
  OUTRO: "Outro",
};

/** Normaliza motivo vindo da API (enum ou texto) para exibição no KPI. */
export function formatCausaFaltaMotivo(motivo: string): string {
  const trimmed = motivo.trim();
  const mapped = MOTIVO_BI_LABELS[trimmed];
  if (mapped) {
    return mapped;
  }
  if (/^ATESTADO/i.test(trimmed)) {
    return "Atestado";
  }
  return trimmed;
}

export function formatPercentualInteiro(percentual: number): string {
  return `${Math.round(percentual)}%`;
}

export function formatRelativeSince(date: Date, now: Date = new Date()): string {
  const diffSec = Math.max(0, Math.floor((now.getTime() - date.getTime()) / 1000));
  if (diffSec < 60) {
    return `há ${diffSec}s`;
  }
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) {
    return `há ${diffMin} min`;
  }
  const diffH = Math.floor(diffMin / 60);
  return `há ${diffH}h`;
}

/**
 * Sprint bi-layout-prototipo: período sem remanejamentos mantém o layout
 * completo (KPIs zerados, gráfico/lista vazios) — nunca página EmptyState.
 */
export function shouldUseBiFullPageEmptyState(_totalRemanejamentos: number): boolean {
  return false;
}
