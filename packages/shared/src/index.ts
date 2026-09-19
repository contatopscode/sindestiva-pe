// =============================================================================
// SINDESTIVA-PE · Shared types
// Placeholder Sprint 0. Conteúdo real entra em Sprint 1 (RBAC, hash chain,
// enums de domínio — Porto, Turno, Faina, Funcao, Role, StatusRemanejamento).
// =============================================================================

export const APP_NAME = "lousa-sindestiva";
export const APP_VERSION = "0.1.0";

/** Roles principais (Sprint 1, T1-04) */
export const ROLES = ["FISCAL", "DIRIGENTE", "TPA", "ADMIN"] as const;
export type Role = (typeof ROLES)[number];

/** Portos cobertos pelo MVP */
export const PORTOS = ["SUAPE", "RECIFE"] as const;
export type Porto = (typeof PORTOS)[number];

/** Turnos portuários */
export const TURNOS = ["DIURNO", "NOTURNO"] as const;
export type Turno = (typeof TURNOS)[number];

/** Status do workflow de notificação ao OGMO (Sprint 5, T5-10) — legado, contexto remanejamento */
export const STATUS_OGMO = ["PEND", "SENT", "ACK", "NACK"] as const;
export type StatusOgmo = (typeof STATUS_OGMO)[number];

/** Status da notificação ao OGMO/PE (HU005) — fila de notificações, 5 valores.
 *  Coexiste com STATUS_OGMO legado (contexto remanejamento) — não misturar. */
export const STATUS_NOTIFICACAO_OGMO = [
  "PENDENTE",
  "ENVIADO",
  "ENTREGUE",
  "FALHOU",
  "REJEITADO",
] as const;
export type StatusNotificacaoOgmo = (typeof STATUS_NOTIFICACAO_OGMO)[number];

export {
  OGMO_RECIFE_DEFAULT_URL,
  OGMO_RECIFE_IFRAME_SANDBOX,
  ogmoRecifeEmbedTargets,
  resolveOgmoRecifeUrl,
} from "./ogmo-recife";
