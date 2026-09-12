// =============================================================================
// SINDESTIVA-PE · Mapeamento API (Pydantic) → tipos de UI do Centro de Comando
// =============================================================================

import type { StatusOgmo } from "@sindestiva/shared";
import type {
  AuditEvent,
  AuditEventKind,
  OgmoNotificacao,
  RemanejamentoItem,
} from "./tipos";

/** Resposta paginada de GET /api/v1/remanejamentos. */
export interface RemanejamentoListResponseApi {
  items: RemanejamentoReadApi[];
  total: number;
  skip: number;
  limit: number;
}

interface RemanejamentoReadApi {
  id: string;
  created_at: string;
  status: string;
  motivo: string;
  codigo_se?: string;
  base_legal_texto_livre?: string | null;
  observacoes?: string | null;
  tpa_in_id?: string | null;
}

export interface OgmoNotificacaoApi {
  id: string;
  remanejamento_id: string;
  canal: string;
  destinatario_email?: string | null;
  status: string;
  tentativas: number;
  erro_detalhes?: string | null;
  enviado_at?: string | null;
  created_at: string;
}

export interface AuditEventApi {
  id: string;
  sequencia: number;
  entity_type: string;
  event_type: string;
  actor_role?: string | null;
  actor_user_id?: string | null;
  payload_after: Record<string, unknown>;
  hash_anterior?: string | null;
  hash_evento: string;
  criado_em: string;
}

function mapRemanejamentoStatus(status: string): StatusOgmo {
  switch (status) {
    case "ACK":
      return "ACK";
    case "NACK":
      return "NACK";
    case "NOTIFICADO_OGMO":
      return "SENT";
    case "PENDENTE":
    case "APROVADO":
    default:
      return "PEND";
  }
}

function mapOgmoNotificacaoStatus(status: string): StatusOgmo {
  switch (status) {
    case "ACK":
      return "ACK";
    case "NACK":
    case "REJEITADO":
      return "NACK";
    case "ENVIADO":
    case "ENTREGUE":
      return "SENT";
    case "PENDENTE":
    case "FALHOU":
    default:
      return "PEND";
  }
}

function mapOgmoCanal(canal: string): OgmoNotificacao["canal"] {
  if (canal === "EMAIL" || canal === "WEBHOOK" || canal === "PAINEL_OGMO") {
    return canal === "PAINEL_OGMO" ? "PAINEL" : canal;
  }
  return "EMAIL";
}

export function mapRemanejamentoRead(r: RemanejamentoReadApi): RemanejamentoItem {
  const codigo = r.codigo_se ?? r.id.slice(0, 8);
  return {
    id: String(r.id),
    data_hora: r.created_at,
    tpa_removido_nome: codigo,
    tpa_removido_matricula: "—",
    funcao_codigo: "—",
    faina_codigo: "—",
    motivo: r.motivo,
    base_legal: r.base_legal_texto_livre ?? "—",
    status: mapRemanejamentoStatus(r.status),
    created_by: "—",
    tpa_substituto_nome: r.tpa_in_id ? "Substituto cadastrado" : undefined,
  };
}

export function normalizeRemanejamentosList(
  raw: RemanejamentoItem[] | RemanejamentoListResponseApi,
): RemanejamentoItem[] {
  if (Array.isArray(raw)) {
    return raw.map((item) =>
      "tpa_removido_nome" in item ? item : mapRemanejamentoRead(item as RemanejamentoReadApi),
    );
  }
  return raw.items.map(mapRemanejamentoRead);
}

export function mapOgmoNotificacao(n: OgmoNotificacaoApi): OgmoNotificacao {
  return {
    id: String(n.id),
    data_hora: n.enviado_at ?? n.created_at,
    remanejamento_id: String(n.remanejamento_id),
    canal: mapOgmoCanal(n.canal),
    destinatario: n.destinatario_email ?? "—",
    status: mapOgmoNotificacaoStatus(n.status),
    tentativas: n.tentativas,
    ultimo_erro: n.erro_detalhes ?? undefined,
  };
}

function inferAuditKind(entityType: string, eventType: string): AuditEventKind {
  const et = entityType.toLowerCase();
  const ev = eventType.toUpperCase();
  if (et.includes("scrap") || et.includes("lousa_snapshot")) {
    if (ev.includes("ERRO")) return "SCRAPING_ERRO";
    if (ev.includes("PARCIAL")) return "SCRAPING_PARCIAL";
    if (ev.includes("LAYOUT")) return "LAYOUT_MUDOU";
    return "SCRAPING_OK";
  }
  if (et.includes("remanejamento")) {
    if (ev.includes("STATUS") || ev.includes("ENV")) return "REMANEJAMENTO_ENVIADO";
    return "REMANEJAMENTO_CRIADO";
  }
  if (ev.includes("LOGIN")) return "LOGIN";
  if (ev.includes("LOGOUT")) return "LOGOUT";
  if (ev.includes("ACK")) return "OGMO_ACK";
  if (ev.includes("NACK")) return "OGMO_NACK";
  return "LOGIN";
}

function auditDescription(e: AuditEventApi): string {
  const payload = e.payload_after;
  const msg = payload.message ?? payload.descricao ?? payload.detail;
  if (typeof msg === "string" && msg.trim() !== "") return msg;
  return `${e.entity_type} · ${e.event_type}`;
}

export function mapAuditEvent(e: AuditEventApi): AuditEvent {
  const actor =
    e.actor_role ??
    (e.actor_user_id ? `usuário ${String(e.actor_user_id).slice(0, 8)}…` : "sistema");
  return {
    id: String(e.id),
    created_at: e.criado_em,
    kind: inferAuditKind(e.entity_type, e.event_type),
    actor,
    descricao: auditDescription(e),
    hash_evento: e.hash_evento,
    hash_anterior: e.hash_anterior ?? "—",
    verificado: false,
  };
}

export function shortHashPrefix(hash: string, len = 16): string {
  if (hash === "—" || hash.length <= len) return hash;
  return `${hash.slice(0, len)}…`;
}
