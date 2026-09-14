// =============================================================================
// SINDESTIVA-PE · Helpers de UI — Remanejamentos (badges, KPIs, motivos)
// =============================================================================

import type { MotivoRemanejamentoUi, StatusRemanejamentoUi } from "@/lib/tipos";

/** Labels curtos do protótipo (PEND / SENT / ACK / NACK). */
export type RemanejamentoBadgeLabel = "PEND" | "SENT" | "ACK" | "NACK";

/**
 * Mapeamento de status do backend → badge do protótipo.
 *
 * - PENDENTE → PEND
 * - APROVADO | NOTIFICADO_OGMO → SENT (enviado / em trânsito ao OGMO)
 * - ACK → ACK
 * - NACK | CANCELADO → NACK
 */
export function badgeLabelForRemanejamentoStatus(
  status: StatusRemanejamentoUi,
): RemanejamentoBadgeLabel {
  switch (status) {
    case "PENDENTE":
      return "PEND";
    case "APROVADO":
    case "NOTIFICADO_OGMO":
      return "SENT";
    case "ACK":
      return "ACK";
    case "NACK":
    case "CANCELADO":
      return "NACK";
    default:
      return "PEND";
  }
}

export function cssClassForRemanejamentoBadge(
  label: RemanejamentoBadgeLabel,
): string {
  switch (label) {
    case "PEND":
      return "status-pend";
    case "SENT":
      return "status-sent";
    case "ACK":
      return "status-ack";
    case "NACK":
      return "status-nack";
    default:
      return "status-pend";
  }
}

const MOTIVO_LABELS: Record<MotivoRemanejamentoUi, string> = {
  ATESTADO_MEDICO: "Atestado médico (NR-7)",
  FALTA_INJUSTIFICADA: "Falta injustificada",
  REFORCO_TERNO: "Reforço de terno",
  TROCA_TURNO: "Troca de turno",
  ATRASO_15MIN: "Atraso superior a 15 min",
  FALTA_EPI: "Falta de EPI",
  LIBERACAO_ANTECIPADA: "Liberação antecipada",
  OUTRO: "Outro",
};

export function labelForMotivo(motivo: MotivoRemanejamentoUi): string {
  return MOTIVO_LABELS[motivo] ?? motivo;
}

/** Texto de motivo para a linha do histórico (enum + detalhe opcional). */
export function formatMotivoLinha(
  motivo: MotivoRemanejamentoUi,
  motivoOutro: string | null | undefined,
): string {
  if (motivo === "OUTRO" && motivoOutro?.trim()) {
    return motivoOutro.trim();
  }
  const base = labelForMotivo(motivo);
  if (motivoOutro?.trim()) {
    return `${base} — ${motivoOutro.trim()}`;
  }
  return base;
}

export interface RemanejamentoKpis {
  totalHoje: number;
  aceitosOgmo: number;
  taxaAceitosPct: number;
  pendentes: number;
  recusados: number;
}

export function isReferenciaHoje(
  dataReferencia: string,
  createdAt: string,
  hojeIso: string,
): boolean {
  if (dataReferencia === hojeIso) return true;
  const createdDay = createdAt.slice(0, 10);
  return createdDay === hojeIso;
}

export function computeRemanejamentoKpis(
  items: Array<{ status: StatusRemanejamentoUi; data_referencia: string; created_at: string }>,
  hojeIso: string,
): RemanejamentoKpis {
  const hoje = items.filter((r) =>
    isReferenciaHoje(r.data_referencia, r.created_at, hojeIso),
  );
  const totalHoje = hoje.length;
  const aceitosOgmo = hoje.filter((r) => r.status === "ACK").length;
  const pendentes = hoje.filter((r) => r.status === "PENDENTE").length;
  const recusados = hoje.filter(
    (r) => r.status === "NACK" || r.status === "CANCELADO",
  ).length;
  const taxaAceitosPct =
    totalHoje > 0 ? Math.round((aceitosOgmo / totalHoje) * 100) : 0;
  return { totalHoje, aceitosOgmo, taxaAceitosPct, pendentes, recusados };
}

export function borderClassForRemanejamentoItem(
  status: StatusRemanejamentoUi,
): string {
  const label = badgeLabelForRemanejamentoStatus(status);
  if (label === "NACK") return "border-l-[3px] border-l-[#e04a4a]";
  if (label === "ACK") return "border-l-[3px] border-l-[#5dbb7d] opacity-90";
  if (label === "PEND") return "border-l-[3px] border-l-[#e8a33d]";
  return "border-l-[3px] border-l-[#4fb8c9]";
}
