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

/** Status do workflow de notificação ao OGMO (Sprint 5, T5-10) */
export const STATUS_OGMO = ["PEND", "SENT", "ACK", "NACK"] as const;
export type StatusOgmo = (typeof STATUS_OGMO)[number];
