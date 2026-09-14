// =============================================================================
// SINDESTIVA-PE · Tipos do Centro de Comando
// Espelha os schemas Pydantic de `apps/api/app/schemas/lousa.py`,
// `apps/api/app/schemas/remanejamento.py` e `apps/api/app/schemas/ogmo.py`
// (Sprint S2 — frontend com dados reais).
//
// Para o enum `STATUS_NOTIFICACAO_OGMO` (5 valores da fila OGMO) usamos o
// tipo derivado de `@sindestiva/shared` e o reexportamos localmente como
// `StatusNotificacaoUi` para isolar a fronteira UI ↔ domínio.
//
// =============================================================================

import type { Porto, StatusNotificacaoOgmo, Turno } from "@sindestiva/shared";

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

// ---- CCT (catálogo de cláusulas da Convenção Coletiva) ---------------------

/**
 * Cláusula da CCT (Convenção Coletiva de Trabalho) usada como base legal
 * do remanejamento. Espelha `apps/api/app/models/catalogos.py:CctClausula`.
 *
 * O frontend recebe via prop opcional `cctClausulas` no modal; quando
 * ausente (lacuna L02-Front — `LousaPreviewResponse` ainda não traz o
 * catálogo), o modal abre direto com o textarea de texto livre.
 */
export interface CctClausula {
  id: string; // UUID
  versao_cct: string; // ex.: "2024-2026"
  clausula: string; // ex.: "cl. 12ª, §3º"
  descricao: string;
  motivos_vinculados: string[] | null;
  is_active: boolean;
}

/** Opção de TPA substituto derivada de `cells[]` do catálogo. */
export interface TpaOption {
  tpa_id: string;
  tpa_nome: string;
  tpa_matricula: string | null;
}

// ---- Snapshot --------------------------------------------------------------

export type SnapshotStatus = "OK" | "PARCIAL" | "ERRO" | "LAYOUT_MUDOU" | "SEM_DADOS";

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

// ---- Remanejamento (casado com `RemanejamentoRead` / `RemanejamentoBase`) -

/**
 * Status do remanejamento no ciclo de vida (espelha `StatusRemanejamentoEnum`
 * em `apps/api/app/models/enums.py`). Exposto como union de strings para que
 * o UI possa tratar o valor cru que vem do backend sem precisar importar o
 * enum Python.
 */
export type StatusRemanejamentoUi =
  | "PENDENTE"
  | "APROVADO"
  | "NOTIFICADO_OGMO"
  | "ACK"
  | "NACK"
  | "CANCELADO";

/** Motivo do remanejamento (espelha `MotivoRemanejamentoEnum`). */
export type MotivoRemanejamentoUi =
  | "ATESTADO_MEDICO"
  | "FALTA_INJUSTIFICADA"
  | "REFORCO_TERNO"
  | "TROCA_TURNO"
  | "ATRASO_15MIN"
  | "FALTA_EPI"
  | "LIBERACAO_ANTECIPADA"
  | "OUTRO";

/**
 * Item de remanejamento para a UI.
 *
 * Espelha `apps/api/app/schemas/remanejamento.py:RemanejamentoRead` —
 * IDs são UUIDs, `status`/`motivo` vêm como string do enum do backend
 * (sem colapso). Resolução de nomes para exibição acontece no mapper
 * (`mapRemanejamentoRead`) usando `LousaPreviewResponse.cells[]` e
 * catálogos carregados em paralelo.
 */
export interface RemanejamentoItem {
  id: string; // UUID
  codigo_se: string;
  fiscal_id: string; // UUID
  snapshot_origem_id: string | null; // UUID
  porto_id: string; // UUID
  turno_id: string; // UUID
  data_referencia: string; // YYYY-MM-DD
  tpa_out_id: string; // UUID
  tpa_in_id: string | null; // UUID
  funcao_origem_id: string; // UUID
  faina_origem_id: string; // UUID
  cais_origem: string | null;
  status: StatusRemanejamentoUi;
  motivo: MotivoRemanejamentoUi;
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
  created_at: string; // ISO
  updated_at: string; // ISO
}

/**
 * Payload de criação do remanejamento.
 *
 * Espelha `apps/api/app/schemas/remanejamento.py:RemanejamentoBase` — sem
 * `notify_pwa`/`ack_cct` (removidos na Sprint S2, ver L03-Front).
 */
export interface RemanejamentoCreate {
  porto_id: string;
  turno_id: string;
  data_referencia: string; // YYYY-MM-DD
  tpa_out_id: string;
  funcao_origem_id: string;
  faina_origem_id: string;
  cais_origem?: string | null;
  tpa_in_id?: string | null;
  motivo: MotivoRemanejamentoUi;
  motivo_outro_texto?: string | null;
  base_legal_cct_id?: string | null;
  base_legal_texto_livre?: string | null;
  observacoes?: string | null;
  anexo_url?: string | null;
  snapshot_origem_id?: string | null;
}

/**
 * Resposta de `POST /api/v1/remanejamentos/{id}/notificar-ogmo` e
 * `POST /api/v1/ogmo/notificacoes/{remanejamento_id}/enviar`.
 *
 * Reflete os campos serializados pelo backend em
 * `apps/api/app/api/v1/remanejamentos.py` (linhas 138-167) e
 * `apps/api/app/api/v1/ogmo.py` (linhas 53-92).
 */
export interface NotifyOgmoResponse {
  id: string;
  remanejamento_id: string;
  status: StatusNotificacaoUi;
  canal: string;
  destinatario: string | null;
  payload_hash_sha256: string;
  enviado_at: string | null;
  provider_message_id: string | null;
  erro_detalhes: string | null;
  pdf_anexo_url: string | null;
  tentativas: number;
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
  | "LOGOUT"
  | "OUTRO";

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

/**
 * Status da notificação ao OGMO/PE na fila (5 valores do
 * `StatusNotificacaoEnum`). Reexportado localmente a partir do enum
 * compartilhado para isolar a fronteira UI ↔ domínio e tornar
 * importável em arquivos que ainda não importam `@sindestiva/shared`.
 */
export type StatusNotificacaoUi = StatusNotificacaoOgmo;

export interface OgmoNotificacao {
  id: string;
  data_hora: string;
  remanejamento_id: string;
  canal: "EMAIL" | "WEBHOOK" | "PAINEL" | "WHATSAPP";
  destinatario: string;
  status: StatusNotificacaoUi;
  tentativas: number;
  ultimo_erro?: string;
  /** URL do PDF anexo (quando disponível) — usado pelo tooltip E36. */
  pdf_anexo_url?: string | null;
  /** ID do provider (Evolution/SMTP) — usado pelo tooltip E21. */
  provider_message_id?: string | null;
  /** Timestamp ISO da entrega efetiva (status ENTREGUE). */
  entregue_at?: string | null;
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
  SEM_DADOS: "Sem TPAs no turno",
};
