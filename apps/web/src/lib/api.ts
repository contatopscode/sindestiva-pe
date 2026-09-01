// =============================================================================
// SINDESTIVA-PE · API client + mock fallback
// Wrapper de fetch com:
//   - base URL configurável via NEXT_PUBLIC_API_URL (default 127.0.0.1:8000)
//   - header Authorization: Bearer <jwt> (lido do localStorage)
//   - redirect pra /login em 401
//   - fallback pra MOCK quando API offline (console.log pra debug)
//
// TODO Sprint 1: trocar `localStorage` por sessão NextAuth + httpOnly cookie.
// TODO Sprint 1: padronizar erros com `Problem Details (RFC 7807)` que a API já
//                emite — capturar `detail` e mapear pra UI.
// =============================================================================

import type { Porto, Turno } from "@sindestiva/shared";
import { getMockLousaPreview, MOCK_REMANEJAMENTOS, MOCK_OGMO, MOCK_AUDIT, MOCK_SESSION } from "./mock";
import type {
  LousaPreviewResponse,
  RemanejamentoItem,
  OgmoNotificacao,
  AuditEvent,
  UserSession,
} from "./tipos";

// ---- Configuração ---------------------------------------------------------

const DEFAULT_API_URL = "http://127.0.0.1:8000";

/** Base URL da API. Configurável via `NEXT_PUBLIC_API_URL` no .env do web. */
export const API_URL: string =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  DEFAULT_API_URL;

const STORAGE_KEY_TOKEN = "sindestiva.jwt";
const STORAGE_KEY_USER = "sindestiva.user";

// ---- Auth helpers ---------------------------------------------------------

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token === null) {
    window.localStorage.removeItem(STORAGE_KEY_TOKEN);
  } else {
    window.localStorage.setItem(STORAGE_KEY_TOKEN, token);
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY_TOKEN);
}

export function setUser(user: UserSession | null) {
  if (typeof window === "undefined") return;
  if (user === null) {
    window.localStorage.removeItem(STORAGE_KEY_USER);
  } else {
    window.localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(user));
  }
}

export function getUser(): UserSession | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY_USER);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserSession;
  } catch {
    return null;
  }
}

export function logout() {
  setToken(null);
  setUser(null);
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

// ---- Fetch wrapper --------------------------------------------------------

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`[${status}] ${detail}`);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

export interface ApiOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Quando true, NÃO repassa Authorization (usado em /public/*). */
  noAuth?: boolean;
  /** Quando true, NÃO redireciona em 401 (usado em fluxos de auth). */
  noRedirect?: boolean;
  /** Timeout em ms (default 8000). */
  timeoutMs?: number;
}

/**
 * Fetch com auth, timeout e tratamento de erro padronizado.
 * Lança `ApiError` em status >= 400. Em status 401 + auto-redirect, manda
 * pro /login (a menos que `noRedirect` seja true).
 */
export async function apiFetch<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, noAuth = false, noRedirect = false, timeoutMs = 8000 } = opts;

  const url = `${API_URL}${path.startsWith("/") ? path : `/${path}`}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (!noAuth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: ac.signal,
      credentials: "include",
    });
  } catch (err) {
    clearTimeout(timer);
    const msg = err instanceof Error ? err.message : String(err);
    throw new ApiError(0, `Falha de rede: ${msg}`);
  }
  clearTimeout(timer);

  if (res.status === 401 && !noRedirect) {
    setToken(null);
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = (await res.json()) as { detail?: string };
      if (j?.detail) detail = j.detail;
    } catch {
      /* body não é JSON */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---- Endpoints de Lousa ---------------------------------------------------

/**
 * GET /api/v1/lousa/public/preview?porto=X&turno=Y
 *
 * Em Sprint 0 é público (sem auth). Sprint 1 vira autenticado
 * (renomear pra /lousa/atual).
 *
 * Fallback: se API offline, retorna mock determinístico + log.
 */
export async function getLousaPreview(
  porto: Porto,
  turno: Turno,
  useMockIfOffline = true,
): Promise<LousaPreviewResponse> {
  try {
    return await apiFetch<LousaPreviewResponse>(
      `/api/v1/lousa/public/preview?porto=${porto}&turno=${turno}`,
      { noAuth: true, timeoutMs: 4000 },
    );
  } catch (err) {
    if (!useMockIfOffline) throw err;
    if (typeof console !== "undefined") {
      console.warn(`[MOCK] usando dados locais (API offline): ${(err as Error).message}`);
    }
    return getMockLousaPreview(porto, turno);
  }
}

// ---- Endpoints de Remanejamento (Sprint 0 = mock) ------------------------

/** Lista remanejamentos do turno/data. Sprint 5 implementa de verdade. */
export async function getRemanejamentos(filters?: {
  turno?: Turno;
  data?: string;
}): Promise<RemanejamentoItem[]> {
  try {
    return await apiFetch<RemanejamentoItem[]>("/api/v1/remanejamentos", {
      body: filters as unknown as Record<string, string>,
      method: "GET",
    });
  } catch {
    if (typeof console !== "undefined") {
      console.warn("[MOCK] usando remanejamentos locais");
    }
    return MOCK_REMANEJAMENTOS;
  }
}

export async function createRemanejamento(input: unknown): Promise<RemanejamentoItem> {
  // Sprint 5: POST /api/v1/remanejamentos
  return new Promise((resolve) => {
    setTimeout(() => {
      const novo: RemanejamentoItem = {
        id: `rem-${Date.now()}`,
        data_hora: new Date().toISOString(),
        tpa_removido_nome: "(novo)",
        tpa_removido_matricula: "000",
        funcao_codigo: "CM_GERAL",
        faina_codigo: "PRODUCAO",
        motivo: "(criado via UI mock)",
        base_legal: "CCT 2024-2026 · Cláusula 7ª",
        status: "PEND",
        created_by: MOCK_SESSION.nome,
        hash_evento: `mock-${Math.random().toString(36).slice(2, 10)}`,
      };
      resolve(novo);
    }, 400);
  });
}

// ---- OGMO -----------------------------------------------------------------

export async function getOgmoNotificacoes(): Promise<OgmoNotificacao[]> {
  try {
    return await apiFetch<OgmoNotificacao[]>("/api/v1/ogmo/notificacoes");
  } catch {
    if (typeof console !== "undefined") console.warn("[MOCK] usando OGMO local");
    return MOCK_OGMO;
  }
}

// ---- Auditoria ------------------------------------------------------------

export async function getAuditEvents(limit = 50): Promise<AuditEvent[]> {
  try {
    return await apiFetch<AuditEvent[]>(`/api/v1/auditoria/eventos?limit=${limit}`);
  } catch {
    if (typeof console !== "undefined") console.warn("[MOCK] usando auditoria local");
    return MOCK_AUDIT.slice(0, limit);
  }
}

/** Verifica integridade da hash chain. Sprint 6 implementa. */
export async function verifyHashChain(): Promise<{ ok: boolean; verificados: number; quebrados: number }> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ ok: true, verificados: MOCK_AUDIT.length, quebrados: 0 });
    }, 600);
  });
}

// ---- Sessão (mock) --------------------------------------------------------

export function getCurrentUser(): UserSession {
  const stored = getUser();
  return stored ?? MOCK_SESSION;
}
