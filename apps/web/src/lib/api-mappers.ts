// =============================================================================
// SINDESTIVA-PE · Mapeamento API (Pydantic) → tipos de UI do Centro de Comando
//
// Sprint S2 — dados reais:
//   - `mapRemanejamentoStatus` devolve string do `StatusRemanejamentoEnum`
//     sem colapsar `NOTIFICADO_OGMO` em `SENT`.
//   - `mapOgmoNotificacaoStatus` mapeia os 5 valores do enum para o
//     `StatusNotificacaoUi` (sem perda de informação).
//   - `mapRemanejamentoRead` resolve nomes legíveis (TPA/matrícula, faina/
//     função) a partir do catálogo `LousaPreviewResponse` carregado em
//     paralelo (D01/D02).
//   - `inferAuditKind` cobre LOGIN/LOGOUT explicitamente ANTES do ramo
//     genérico OGMO_ACK/NACK (D05).
//   - `mapAuditEvent` prefere `actor_nome` quando o backend entrega,
//     formatando `<actor_nome> · <actor_role>` (U+00B7, D10/D12).
// =============================================================================

import type {
  AuditEvent,
  AuditEventKind,
  Faina,
  Funcao,
  LousaCellOut,
  MotivoRemanejamentoUi,
  OgmoNotificacao,
  RemanejamentoItem,
  StatusNotificacaoUi,
  StatusRemanejamentoUi,
} from "./tipos";

/** Resposta paginada de GET /api/v1/remanejamentos. */
export interface RemanejamentoListResponseApi {
  items: RemanejamentoReadApi[];
  total: number;
  skip: number;
  limit: number;
}

/** Payload cru de `RemanejamentoRead` vindo do backend. */
export interface RemanejamentoReadApi {
  id: string;
  codigo_se: string;
  fiscal_id: string;
  snapshot_origem_id: string | null;
  porto_id: string;
  turno_id: string;
  data_referencia: string;
  tpa_out_id: string;
  tpa_in_id: string | null;
  funcao_origem_id: string;
  faina_origem_id: string;
  cais_origem: string | null;
  status: string;
  motivo: string;
  motivo_outro_texto: string | null;
  base_legal_cct_id: string | null;
  base_legal_texto_livre: string | null;
  observacoes: string | null;
  anexo_url: string | null;
  ack_at: string | null;
  ack_por: string | null;
  nack_motivo: string | null;
  hash_evento: string;
  hash_anterior_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OgmoNotificacaoApi {
  id: string;
  remanejamento_id: string;
  canal: string;
  destinatario_email?: string | null;
  destinatario_whatsapp?: string | null;
  status: string;
  tentativas: number;
  erro_detalhes?: string | null;
  provider_message_id?: string | null;
  pdf_anexo_url?: string | null;
  enviado_at?: string | null;
  criado_em?: string | null;
  entregue_at?: string | null;
  created_at: string;
}

export interface AuditEventApi {
  id: string;
  sequencia: number;
  entity_type: string;
  event_type: string;
  actor_role?: string | null;
  actor_user_id?: string | null;
  actor_nome?: string | null;
  actor_user_email?: string | null;
  payload_after: Record<string, unknown>;
  hash_anterior?: string | null;
  hash_evento: string;
  criado_em: string;
}

/** Conjunto completo de status válidos de `StatusRemanejamentoEnum`. */
const STATUS_REMANEJAMENTO_VALIDOS: readonly StatusRemanejamentoUi[] = [
  "PENDENTE",
  "APROVADO",
  "NOTIFICADO_OGMO",
  "ACK",
  "NACK",
  "CANCELADO",
];

/** Conjunto completo de status válidos de `StatusNotificacaoEnum` (5 valores). */
const STATUS_NOTIFICACAO_VALIDOS: readonly StatusNotificacaoUi[] = [
  "PENDENTE",
  "ENVIADO",
  "ENTREGUE",
  "FALHOU",
  "REJEITADO",
];

const MOTIVO_VALIDOS: readonly MotivoRemanejamentoUi[] = [
  "ATESTADO_MEDICO",
  "FALTA_INJUSTIFICADA",
  "REFORCO_TERNO",
  "TROCA_TURNO",
  "ATRASO_15MIN",
  "FALTA_EPI",
  "LIBERACAO_ANTECIPADA",
  "OUTRO",
];

function isStatusRemanejamento(s: string): s is StatusRemanejamentoUi {
  return (STATUS_REMANEJAMENTO_VALIDOS as readonly string[]).includes(s);
}

function isStatusNotificacao(s: string): s is StatusNotificacaoUi {
  return (STATUS_NOTIFICACAO_VALIDOS as readonly string[]).includes(s);
}

function asMotivo(value: string): MotivoRemanejamentoUi {
  return (MOTIVO_VALIDOS as readonly string[]).includes(value)
    ? (value as MotivoRemanejamentoUi)
    : "OUTRO";
}

/**
 * Converte o `status` cru do backend em `StatusRemanejamentoUi`.
 *
 * NÃO colapsa `NOTIFICADO_OGMO` em `SENT` — preserva o valor para que o
 * badge e os KPIs da tabela de remanejamentos exibam o estado real.
 * Valores desconhecidos caem em `PENDENTE` (fallback conservador: o
 * fiscal precisa ver o item, não escondê-lo).
 */
function mapRemanejamentoStatus(status: string): StatusRemanejamentoUi {
  if (isStatusRemanejamento(status)) return status;
  return "PENDENTE";
}

/**
 * Converte o `status` cru da fila OGMO em `StatusNotificacaoUi`.
 *
 * Diferente do mapper antigo, NÃO colapsa `FALHOU`/`REJEITADO` em
 * `NACK` (são conceitos distintos — fila OGMO × workflow de
 * remanejamento). Cobertura 1-para-1: 5 entradas → 5 valores.
 */
function mapOgmoNotificacaoStatus(status: string): StatusNotificacaoUi {
  if (isStatusNotificacao(status)) return status;
  return "PENDENTE";
}

function mapOgmoCanal(canal: string): OgmoNotificacao["canal"] {
  if (canal === "EMAIL" || canal === "WEBHOOK" || canal === "PAINEL_OGMO") {
    return canal === "PAINEL_OGMO" ? "PAINEL" : canal;
  }
  if (canal === "WHATSAPP") return "WHATSAPP";
  return "EMAIL";
}

/** Catálogo necessário para resolver nomes legíveis do remanejamento. */
export interface RemanejamentoCatalogo {
  cells: LousaCellOut[];
  fainas: Faina[];
  funcoes: Funcao[];
}

/**
 * Item de remanejamento JÁ mapeado + dados resolvidos via catálogo.
 *
 * Estende `RemanejamentoItem` com campos auxiliares consumidos pela
 * tabela (sem inflar o tipo cru que vem do backend).
 */
export interface RemanejamentoItemResolved extends RemanejamentoItem {
  /** Nome do TPA removido (resolvido via `cells[]` do catálogo). */
  tpa_removido_nome: string;
  /** Matrícula OGMO do TPA removido (resolvido via `cells[]`). */
  tpa_removido_matricula: string;
  /** Nome do TPA substituto, se houver. */
  tpa_substituto_nome?: string;
  /** Nome da faina de origem (resolvido via catálogo de fainas). */
  funcao_origem_nome: string;
  /** Código da função de origem (resolvido via catálogo de funções). */
  funcao_origem_codigo: string;
  /** Nome da faina de origem (resolvido via catálogo de fainas). */
  faina_origem_nome: string;
  /** Código da faina de origem (resolvido via catálogo de fainas). */
  faina_origem_codigo: string;
  /** Texto de base legal livre, exibido na coluna "Base legal". */
  base_legal_texto: string;
}

/**
 * Converte um `RemanejamentoReadApi` em `RemanejamentoItemResolved`
 * consumível pela UI.
 *
 * Resolução de nomes (D01/D02): a UI NÃO recebe `tpa_out`/`tpa_in`/
 * `fiscal`/`funcao`/`faina` como objetos (ver L01-Front). Usamos o
 * catálogo `LousaPreviewResponse` carregado em paralelo via
 * `getLousaPreview(porto, turno)`. Quando o catálogo está vazio ou o
 * ID não bate, devolvemos `(nome removido)` para deixar claro que o
 * dado existe, mas o lookup falhou (TPA desligado, turno SEM_DADOS,
 * snapshot de outro porto/turno).
 */
export function mapRemanejamentoRead(
  r: RemanejamentoReadApi,
  catalogo?: RemanejamentoCatalogo,
): RemanejamentoItemResolved {
  const cells = catalogo?.cells ?? [];
  const cellOut = cells.find((c) => c.tpa_id === r.tpa_out_id) ?? null;
  const cellIn = r.tpa_in_id ? cells.find((c) => c.tpa_id === r.tpa_in_id) ?? null : null;
  const funcao = catalogo?.funcoes.find((f) => f.id === r.funcao_origem_id) ?? null;
  const faina = catalogo?.fainas.find((f) => f.id === r.faina_origem_id) ?? null;

  const item: RemanejamentoItem = {
    id: String(r.id),
    codigo_se: r.codigo_se,
    fiscal_id: String(r.fiscal_id),
    snapshot_origem_id: r.snapshot_origem_id ? String(r.snapshot_origem_id) : null,
    porto_id: String(r.porto_id),
    turno_id: String(r.turno_id),
    data_referencia: r.data_referencia,
    tpa_out_id: String(r.tpa_out_id),
    tpa_in_id: r.tpa_in_id ? String(r.tpa_in_id) : null,
    funcao_origem_id: String(r.funcao_origem_id),
    faina_origem_id: String(r.faina_origem_id),
    cais_origem: r.cais_origem ?? null,
    status: mapRemanejamentoStatus(r.status),
    motivo: asMotivo(r.motivo),
    motivo_outro_texto: r.motivo_outro_texto ?? null,
    base_legal_cct_id: r.base_legal_cct_id ? String(r.base_legal_cct_id) : null,
    base_legal_texto_livre: r.base_legal_texto_livre ?? null,
    observacoes: r.observacoes ?? null,
    anexo_url: r.anexo_url ?? null,
    ack_at: r.ack_at ?? null,
    ack_por: r.ack_por ?? null,
    nack_motivo: r.nack_motivo ?? null,
    hash_evento: r.hash_evento,
    hash_anterior_id: r.hash_anterior_id ? String(r.hash_anterior_id) : null,
    created_at: r.created_at,
    updated_at: r.updated_at,
  };

  const resolved: RemanejamentoItemResolved = {
    ...item,
    tpa_removido_nome: cellOut?.tpa_nome ?? "(nome removido)",
    tpa_removido_matricula: cellOut?.tpa_matricula ?? "—",
    funcao_origem_nome: funcao?.nome ?? "(função removida)",
    funcao_origem_codigo: funcao?.codigo ?? "—",
    faina_origem_nome: faina?.nome ?? "(faina removida)",
    faina_origem_codigo: faina?.codigo ?? "—",
    base_legal_texto: r.base_legal_texto_livre ?? "—",
  };

  if (cellIn?.tpa_nome) {
    resolved.tpa_substituto_nome = cellIn.tpa_nome;
  } else if (r.tpa_in_id) {
    resolved.tpa_substituto_nome = "(nome removido)";
  }

  return resolved;
}

export function normalizeRemanejamentosList(
  raw: RemanejamentoItemResolved[] | RemanejamentoListResponseApi,
  catalogo?: RemanejamentoCatalogo,
): RemanejamentoItemResolved[] {
  if (Array.isArray(raw)) {
    return raw.map((item) =>
      "tpa_removido_nome" in item
        ? item
        : mapRemanejamentoRead(item as unknown as RemanejamentoReadApi, catalogo),
    );
  }
  return raw.items.map((it) => mapRemanejamentoRead(it, catalogo));
}

export function mapOgmoNotificacao(n: OgmoNotificacaoApi): OgmoNotificacao {
  return {
    id: String(n.id),
    data_hora: n.enviado_at ?? n.criado_em ?? n.created_at,
    remanejamento_id: String(n.remanejamento_id),
    canal: mapOgmoCanal(n.canal),
    destinatario: n.destinatario_email ?? n.destinatario_whatsapp ?? "—",
    status: mapOgmoNotificacaoStatus(n.status),
    tentativas: n.tentativas,
    ultimo_erro: n.erro_detalhes ?? undefined,
    pdf_anexo_url: n.pdf_anexo_url ?? null,
    provider_message_id: n.provider_message_id ?? null,
    entregue_at: n.entregue_at ?? null,
  };
}

/**
 * Infere o `AuditEventKind` a partir de `entity_type` e `event_type`.
 *
 * Regra explícita: LOGIN/LOGOUT são checados ANTES do ramo OGMO_ACK/NACK
 * para que `event_type="LOGIN"` seja classificado corretamente mesmo se
 * algum dia a string contiver "ACK" (defesa em profundidade — D05).
 */
function inferAuditKind(entityType: string, eventType: string): AuditEventKind {
  const et = entityType.toLowerCase();
  const ev = eventType.toUpperCase();
  // LOGIN/LOGOUT primeiro — antes de OGMO_ACK/NACK (D05).
  if (ev === "LOGIN") return "LOGIN";
  if (ev === "LOGOUT") return "LOGOUT";
  if (et.includes("scrap") || et.includes("lousa_snapshot") || et.includes("lousa_alocacao")) {
    if (ev.includes("ERRO") || ev.includes("FALHA")) return "SCRAPING_ERRO";
    if (ev.includes("PARCIAL")) return "SCRAPING_PARCIAL";
    if (ev.includes("LAYOUT")) return "LAYOUT_MUDOU";
    return "SCRAPING_OK";
  }
  if (et.includes("remanejamento")) {
    if (ev.includes("STATUS") || ev.includes("ENV")) return "REMANEJAMENTO_ENVIADO";
    return "REMANEJAMENTO_CRIADO";
  }
  if (et.includes("ogmo")) {
    if (ev.includes("ACK")) return "OGMO_ACK";
    if (ev.includes("NACK") || ev.includes("REJEIT")) return "OGMO_NACK";
    return "OGMO_ACK";
  }
  if (ev.includes("ACK")) return "OGMO_ACK";
  if (ev.includes("NACK")) return "OGMO_NACK";
  // Sentinel neutro para entity_types/event_types não classificados
  // (ex.: LGDP_SOLICITACAO, BI_EXPORT, AUTH_*) — evita que um evento
  // desconhecido seja renderizado como "Login" (CR1 — achado MEDIO da
  // revisão, antes caía em LOGIN e confundia o auditor).
  return "OUTRO";
}

function auditDescription(e: AuditEventApi): string {
  const payload = e.payload_after;
  const msg = payload.message ?? payload.descricao ?? payload.detail;
  if (typeof msg === "string" && msg.trim() !== "") return msg;
  return `${e.entity_type} · ${e.event_type}`;
}

/** Separador U+00B7 (·) entre nome e role, conforme design system (D10). */
const ACTOR_SEP = "\u00B7";

/**
 * Formata o campo `actor` para exibição.
 *
 * Preferência (D12): se o backend trouxer `actor_nome`, usa
 * `<actor_nome> · <actor_role>`; caso contrário, cai para
 * `actor_role ?? "usuário <primeiros-8-chars-do-actor_user_id>…"`.
 */
function formatActor(e: AuditEventApi): string {
  const role = e.actor_role ?? null;
  if (e.actor_nome && e.actor_nome.trim() !== "") {
    return role ? `${e.actor_nome} ${ACTOR_SEP} ${role}` : e.actor_nome;
  }
  if (role) return role;
  if (e.actor_user_id) {
    return `usuário ${String(e.actor_user_id).slice(0, 8)}\u2026`;
  }
  return "sistema";
}

export function mapAuditEvent(e: AuditEventApi): AuditEvent {
  return {
    id: String(e.id),
    created_at: e.criado_em,
    kind: inferAuditKind(e.entity_type, e.event_type),
    actor: formatActor(e),
    descricao: auditDescription(e),
    hash_evento: e.hash_evento,
    hash_anterior: e.hash_anterior ?? "—",
    verificado: false,
  };
}

export function shortHashPrefix(hash: string, len = 16): string {
  if (hash === "—" || hash.length <= len) return hash;
  return `${hash.slice(0, len)}\u2026`;
}
