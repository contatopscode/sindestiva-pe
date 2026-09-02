// =============================================================================
// SINDESTIVA-PE · Tipos do Centro de Comando
// Espelha os schemas Pydantic de `apps/api/app/schemas/lousa.py` e
// `apps/api/app/api/v1/lousa_public.py` (Sprint 0).
//
// Quando Sprint 1 fechar (RBAC + NextAuth) e Sprint 2 fechar (scraping real),
// estes tipos podem ser compartilhados via `@sindestiva/shared`.
//
// TODO Sprint 1: mover para `packages/shared/src/lousa.ts` e reexportar.
// TODO Sprint 5: incluir `LousaAlocacao` (tabela normalizada) e
//               `RemanejamentoOut` com hash_chain.
// =============================================================================

import type { Porto, Turno, StatusOgmo } from "@sindestiva/shared";

// ---- Catálogos -------------------------------------------------------------

export type FainaCategoria = "PRODUCAO" | "SALARIO" | "SACARIA" | "VEICULO" | "DIVERSOS" | "CADASTRO" | "SUPLEMENTAR" | "ALTURA";

export interface Faina {
  id: string;
  codigo: string;
  nome: string;
  cor_hex: string | null;
  ordem: number;
}

export type FuncaoCategoria = "MANDO" | "TERNO" | "TECNICA" | "VIGIA";

export interface Funcao {
  id: string;
  codigo: string;
  nome: string;
  categoria: FuncaoCategoria;
  ordem: number;
}

// ---- Cell (Lousa) ----------------------------------------------------------

export type CellStatus = "NORMAL" | "AUSENTE" | "REMANEJADO" | "CONFIRMADO";

export interface LousaCellOut {
  id: string;
  faina_id: string;
  funcao_id: string;
  cais: string | null;
  navio_id: string | null;
  tpa_id: string | null;
  tpa_nome: string | null;
  tpa_matricula: string | null;
  status: CellStatus;
  data_referencia: string; // YYYY-MM-DD
}

// ---- Snapshot --------------------------------------------------------------

export type SnapshotStatus = "OK" | "PARCIAL" | "ERRO" | "LAYOUT_MUDOU";

export interface LousaSnapshotOut {
  id: string | null;
  scraped_at: string | null;
  status: SnapshotStatus | null;
  total_celulas: number;
  total_tpas_escalados: number;
  html_hash_sha256?: string; // presente quando o scraper grava fingerprint
  erro_detalhes?: string | null;
}

// ---- Resposta agregada do endpoint /lousa/public/preview -------------------

export interface PortoOut {
  id: string;
  codigo: Porto;
  nome: string;
}

export interface TurnoOut {
  id: string;
  codigo: Turno;
  nome: string;
}

export interface LousaPreviewStats {
  total_cells: number;
  total_tpas_escalados: number;
  total_fainas: number;
  total_funcoes: number;
}

export interface LousaPreviewResponse {
  porto: PortoOut;
  turno: TurnoOut;
  snapshot: LousaSnapshotOut;
  fainas: Faina[];
  funcoes: Funcao[];
  cells: LousaCellOut[];
  stats: LousaPreviewStats;
}

// ---- Remanejamento (UI mock — Sprint 5 implementa de verdade) -------------

export interface RemanejamentoItem {
  id: string;
  data_hora: string; // ISO
  tpa_removido_nome: string;
  tpa_removido_matricula: string;
  funcao_codigo: string;
  faina_codigo: string;
  motivo: string;
  base_legal: string;
  status: StatusOgmo;
  created_by: string; // fiscal
  tpa_substituto_nome?: string;
  hash_evento?: string; // SHA-256
}

export interface RemanejamentoCreate {
  tpa_removido_id: string;
  funcao_codigo: string;
  faina_codigo: string;
  motivo: string;
  base_legal: string;
  observacoes?: string;
  notify_pwa: boolean;
  ack_cct: boolean;
}

// ---- Auditoria (mock — Sprint 6 implementa) -------------------------------

export type AuditEventKind =
  | "SCRAPING_OK"
  | "SCRAPING_ERRO"
  | "SCRAPING_PARCIAL"
  | "LAYOUT_MUDOU"
  | "REMANEJAMENTO_CRIADO"
  | "REMANEJAMENTO_ENVIADO"
  | "OGMO_ACK"
  | "OGMO_NACK"
  | "LOGIN"
  | "LOGOUT";

export interface AuditEvent {
  id: string;
  created_at: string;
  kind: AuditEventKind;
  actor: string;
  descricao: string;
  hash_evento: string;
  hash_anterior: string;
  verificado: boolean;
}

// ---- Notificação OGMO -----------------------------------------------------

export interface OgmoNotificacao {
  id: string;
  data_hora: string;
  remanejamento_id: string;
  canal: "EMAIL" | "WEBHOOK" | "PAINEL";
  destinatario: string;
  status: StatusOgmo;
  tentativas: number;
  ultimo_erro?: string;
}

// ---- Usuário autenticado (mock — Sprint 1 implementa NextAuth) -----------

export interface UserSession {
  id: string;
  nome: string;
  role: "FISCAL" | "DIRIGENTE" | "TPA" | "ADMIN";
  email?: string;
  matricula?: string; // TPA
}

// ---- BI & Dashboards (Sprint 7) ------------------------------------------

export type PeriodoDias = 7 | 30 | 90 | 365;

export interface KpiComparecimento {
  total_escalados: number;
  total_confirmados: number;
  total_ausentes: number;
  percentual: number;
}

export interface KpiFolhaPaga {
  valor_total_brl: number;
  total_remanejamentos: number;
  valor_medio_remanejamento_brl: number;
  periodo_inicio: string;
  periodo_fim: string;
}

export interface KpiCausaPrincipal {
  motivo: string;
  total: number;
  percentual: number;
}

export interface KpiPercentualNack {
  total_notificados: number;
  total_nack: number;
  percentual: number;
}

export interface BIKpis {
  periodo_inicio: string;
  periodo_fim: string;
  comparecimento: KpiComparecimento;
  folha_paga: KpiFolhaPaga;
  causa_principal_falta: KpiCausaPrincipal;
  percentual_nack: KpiPercentualNack;
  gerado_em: string;
}

export interface RemanejamentosPorDiaItem {
  data: string;
  total: number;
}

export interface RemanejamentosPorDia {
  periodo_inicio: string;
  periodo_fim: string;
  items: RemanejamentosPorDiaItem[];
  total: number;
  media_diaria: number;
}

export interface TopRemanejado {
  tpa_id: string;
  tpa_nome: string;
  tpa_matricula: string | null;
  total_remanejamentos: number;
}

export interface TopRemanejados {
  periodo_inicio: string;
  periodo_fim: string;
  items: TopRemanejado[];
}

export interface TopCard {
  label: string;
  total: number;
  percentual: number;
}

export interface TopCards {
  funcao_mais_remanejada: TopCard | null;
  cais_mais_problematico: TopCard | null;
  horario_mais_critico: TopCard | null;
}

export interface Insight {
  severidade: "info" | "alerta" | "critico";
  regra: string;
  mensagem: string;
  tpa_id?: string | null;
  tpa_nome?: string | null;
  total?: number | null;
}

export interface Insights {
  periodo_inicio: string;
  periodo_fim: string;
  items: Insight[];
}

export interface DrillDownItem {
  id: string;
  codigo_se: string;
  tpa_out_nome: string;
  tpa_in_nome: string | null;
  motivo: string;
  status: string;
  data_referencia: string;
  hora_criacao: string;
}

export interface DrillDown {
  data: string;
  items: DrillDownItem[];
  total: number;
}

// ---- Helpers --------------------------------------------------------------

/** Mapeia categoria de função para a classe CSS do protótipo. */
export const CAT_CLASS: Record<FuncaoCategoria, string> = {
  MANDO: "cat-mando",
  TERNO: "cat-terno",
  TECNICA: "cat-tecnica",
  VIGIA: "cat-vigia",
};

/** Mapeia código de faina para classe CSS (do protótipo). */
export const FAINA_CSS_CLASS: Record<string, string> = {
  PRODUCAO: "faina-producao",
  SALARIO: "faina-salario",
  SACARIA: "faina-sacaria",
  VEICULO: "faina-veiculo",
  DIVERSOS: "faina-diversos",
  CADASTRO: "faina-cadastro",
  SUPLEMENTAR: "faina-suplementar",
  ALTURA: "faina-altura",
};

/** Cores de faina (do seed / plano v1.0). */
export const FAINA_COR: Record<string, string> = {
  PRODUCAO: "#2563eb",
  SALARIO: "#16a34a",
  SACARIA: "#ca8a04",
  VEICULO: "#9333ea",
  DIVERSOS: "#64748b",
  CADASTRO: "#0891b2",
  SUPLEMENTAR: "#db2777",
  ALTURA: "#ea580c",
};

/** Label humano da categoria de função. */
export const CAT_LABEL: Record<FuncaoCategoria, string> = {
  MANDO: "Funções de Mando (6)",
  TERNO: "Terno (6)",
  TECNICA: "Funções Técnicas (12)",
  VIGIA: "Vigia (2)",
};

/** Label humano do status de célula. */
export const CELL_STATUS_LABEL: Record<CellStatus, string> = {
  NORMAL: "Presente",
  AUSENTE: "Ausente",
  REMANEJADO: "Remanejado",
  CONFIRMADO: "Confirmado",
};

/** Label humano do status de snapshot. */
export const SNAPSHOT_STATUS_LABEL: Record<SnapshotStatus, string> = {
  OK: "Sincronizado",
  PARCIAL: "Parcial",
  ERRO: "Erro",
  LAYOUT_MUDOU: "Layout mudou",
};
