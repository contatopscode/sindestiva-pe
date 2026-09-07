// =============================================================================
// SINDESTIVA-PE · API client (Sprint B)
//
// Mudanças vs Sprint 0:
//   - Auth via cookie httpOnly `sindestiva_token` (não localStorage).
//     JWT nunca toca o browser → imune a XSS.
//   - fetch envia `credentials: 'include'` para o cookie ir junto.
//   - Removidos fallbacks para MOCK_* (Sprint 1 + tá com dados reais).
//   - Erro 401 → clear cookie + redirect /login (sem reload).
//
// =============================================================================

import type { Porto, Turno } from "@sindestiva/shared";
import type {
  LousaPreviewResponse,
  RemanejamentoItem,
  OgmoNotificacao,
  AuditEvent,
  BIKpis,
  RemanejamentosPorDia,
  TopRemanejados,
  TopCards,
  Insights,
  DrillDown,
  PeriodoDias,
} from "./tipos";

// ---- Configuração ---------------------------------------------------------

const DEFAULT_API_URL = "https://api.lousa.pscode.ia.br";

/** Base URL da API. Configurável via `NEXT_PUBLIC_API_URL` no .env. */
export const API_URL: string =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  DEFAULT_API_URL;

// ---- Auth (cookie httpOnly, gerenciado server-side) -------------------------

/** Limpa o cookie httpOnly e redireciona pra /login. Chamado em 401. */
export async function logout(): Promise<void> {
  if (typeof window === "undefined") return;
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch {
    /* noop */
  }
  window.location.href = "/login";
}

/** Faz login server-side via proxy /api/auth/login (seta cookie httpOnly). */
export async function login(email: string, password: string): Promise<{
  ok: boolean;
  error?: string;
  role?: string;
}> {
  if (typeof window === "undefined") return { ok: false };
  const r = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    credentials: "include",
  });
  if (!r.ok) {
    const data = await r.json().catch(() => ({ error: "Erro desconhecido" }));
    return { ok: false, error: data.error };
  }
  const data = (await r.json()) as { ok: boolean; role?: string };
  return data;
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
 * Fetch com auth via cookie httpOnly, timeout e tratamento de erro padronizado.
 * Lança `ApiError` em status >= 400. Em status 401 + auto-redirect, chama
 * `logout()` (que zera cookie via /api/auth/logout e vai pro /login).
 */
export async function apiFetch<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, noAuth = false, noRedirect = false, timeoutMs = 8000 } = opts;

  const url = `${API_URL}${path.startsWith("/") ? path : `/${path}`}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

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
      mode: "cors",
    });
  } catch (err) {
    clearTimeout(timer);
    const msg = err instanceof Error ? err.message : String(err);
    throw new ApiError(0, `Falha de rede: ${msg}`);
  }
  clearTimeout(timer);

  if (res.status === 401 && !noAuth && !noRedirect) {
    await logout();
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = (await res.json()) as { detail?: unknown };
      if (j?.detail) {
        detail = typeof j.detail === "string"
          ? j.detail
          : JSON.stringify(j.detail);
      }
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
 * Endpoint público (sem auth). Retorna a lousa mais recente do scraper.
 */
export async function getLousaPreview(
  porto: Porto,
  turno: Turno,
): Promise<LousaPreviewResponse> {
  return apiFetch<LousaPreviewResponse>(
    `/api/v1/lousa/public/preview?porto=${porto}&turno=${turno}`,
    { noAuth: true, timeoutMs: 6000 },
  );
}

// ---- Endpoints de Remanejamento (Sprint 5+) -----------------------------

export async function getRemanejamentos(filters?: {
  skip?: number;
  limit?: number;
  status?: string;
}): Promise<RemanejamentoItem[]> {
  const params = new URLSearchParams();
  if (filters?.skip !== undefined) params.set("skip", String(filters.skip));
  if (filters?.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters?.status) params.set("status", filters.status);
  const q = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<RemanejamentoItem[]>(`/api/v1/remanejamentos${q}`);
}

export async function createRemanejamento(
  payload: unknown,
): Promise<RemanejamentoItem> {
  return apiFetch<RemanejamentoItem>("/api/v1/remanejamentos", {
    method: "POST",
    body: payload as Record<string, unknown> | undefined,
  });
}

// ---- OGMO -----------------------------------------------------------------

export async function getOgmoNotificacoes(): Promise<OgmoNotificacao[]> {
  return apiFetch<OgmoNotificacao[]>("/api/v1/ogmo/notificacoes");
}

// ---- Auditoria ------------------------------------------------------------

export async function getAuditEvents(limit = 50): Promise<AuditEvent[]> {
  return apiFetch<AuditEvent[]>(`/api/v1/auditoria/eventos?limit=${limit}`);
}

/** Verifica integridade da hash chain (Sprint 6 — já implementado na API). */
export async function verifyHashChain(): Promise<{
  integro: boolean;
  total_eventos: number;
  primeiro_evento_com_falha: number | null;
  duracao_ms: number;
}> {
  return apiFetch("/api/v1/auditoria/verificar-hash-chain", { method: "POST" });
}

// ---- BI & Dashboards (Sprint 7) -------------------------------------------

/** 4 KPIs (comparecimento, folha paga, causa #1, % NACK). */
export async function getBIKpis(periodoDias: PeriodoDias = 30): Promise<BIKpis> {
  return apiFetch<BIKpis>(`/api/v1/bi/kpis?periodo_dias=${periodoDias}`);
}

/** Série temporal: remanejamentos por dia. */
export async function getBIRemanejamentosPorDia(
  periodoDias: PeriodoDias = 30,
): Promise<RemanejamentosPorDia> {
  return apiFetch<RemanejamentosPorDia>(
    `/api/v1/bi/remanejamentos-por-dia?periodo_dias=${periodoDias}`,
  );
}

/** Drill-down: detalhe dos remanejamentos de 1 dia. */
export async function getBIDrillDown(data: string): Promise<DrillDown> {
  return apiFetch<DrillDown>(`/api/v1/bi/remanejamentos-por-dia/${data}`);
}

/** Ranking top-N TPAs mais remanejados. */
export async function getBITopRemanejados(
  periodoDias: PeriodoDias = 30,
  n = 10,
): Promise<TopRemanejados> {
  return apiFetch<TopRemanejados>(
    `/api/v1/bi/top-remanejados?periodo_dias=${periodoDias}&n=${n}`,
  );
}

/** 3 cards top-1 (função/cais/horário). */
export async function getBITopCards(periodoDias: PeriodoDias = 30): Promise<TopCards> {
  return apiFetch<TopCards>(`/api/v1/bi/top-cards?periodo_dias=${periodoDias}`);
}

/** Insights determinísticos. */
export async function getBIInsights(periodoDias: PeriodoDias = 30): Promise<Insights> {
  return apiFetch<Insights>(`/api/v1/bi/insights?periodo_dias=${periodoDias}`);
}

/** Dispara download do PDF do BI. */
export async function downloadBIPDF(periodoDias: PeriodoDias = 30): Promise<void> {
  const url = `${API_URL}/api/v1/bi/export-pdf?periodo_dias=${periodoDias}`;
  const res = await fetch(url, {
    method: "GET",
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, text || res.statusText);
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `sindestiva-bi-${periodoDias}d.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}
