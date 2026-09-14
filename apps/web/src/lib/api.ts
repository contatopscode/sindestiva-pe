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
import {
  mapAuditEvent,
  mapOgmoNotificacao,
  normalizeRemanejamentosList,
  type AuditEventApi,
  type OgmoNotificacaoApi,
  type RemanejamentoCatalogo,
  type RemanejamentoItemResolved,
  type RemanejamentoListResponseApi,
  type RemanejamentoReadApi,
} from "./api-mappers";
import type {
  LousaPreviewResponse,
  NotifyOgmoResponse,
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

// IMPORTANTE: o front chama a API diretamente via cookie httpOnly.
// Browser compartilha cookies entre subdomínios do mesmo parent domain
// **APENAS** se o cookie foi setado com `Domain=.parent.tld`. Como o
// Next.js 15 stripou nosso `Domain=.pscode.ia.br`, o cookie fica
// scoped a `web.lousa.pscode.ia.br` e NÃO vai pra `api.lousa...`.
//
// Workaround atual (MVP): após login, salvamos o JWT em sessionStorage
// (client-side only) e apiFetch adiciona no header `Authorization`. O
// cookie httpOnly é mantido como fallback p/ middlewares server-side.
//
// Trade-off: token em sessionStorage é vulnerável a XSS (mesmo nível do
// localStorage antigo). Sprint D migra p/ BFF completo (proxy server-side
// sem expor token no browser).

import { buildBffProxyUrl } from "./bff-proxy";
import { DEFAULT_API_URL_DEV, resolveApiUrl } from "./api-url";

/** Dev fallback — origem canônica em api-url.ts (CI C3 whitelist: DEFAULT_API_URL). */
export const DEFAULT_API_URL = DEFAULT_API_URL_DEV;

/** Base URL absoluta da API. Resolvida em build/load via resolveApiUrl(). */
export const API_URL: string = resolveApiUrl();

/** Mesma URL absoluta (sem proxy no MVP). */
export const API_ABSOLUTE_URL = API_URL;

// Storage key p/ JWT em sessionStorage (client-side).
const TOKEN_STORAGE_KEY = "sindestiva.jwt";

/**
 * Decodifica o payload do JWT e retorna o instante de expiração em ms
 * (epoch * 1000) ou null. Robusto a tokens malformados (try/catch).
 *
 * Esta checagem é UX-only: evita enviar token morto no Authorization
 * header. A validação de assinatura continua sendo server-side em
 * apps/api/app/core/security.py.
 */
function jwtExpiresAt(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1] ?? "")) as { exp?: number };
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/**
 * Handle do setTimeout que dispara logout automático ao expirar o JWT.
 * Mantido em escopo de módulo para que `setToken` possa CANCELAR o
 * timer anterior antes de agendar o próximo — sem isso, re-login na
 * mesma sessão SPA acumula timers e o primeiro a disparar apaga o
 * token enquanto ele ainda está válido (logout prematuro).
 */
let logoutTimer: ReturnType<typeof setTimeout> | null = null;

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  // Cancela timer anterior antes de qualquer mudança de estado. Evita
  // que um timer "stale" dispare logout enquanto o token atual ainda
  // é válido (cenário: usuário re-logou e o timer antigo não foi
  // descartado).
  if (logoutTimer !== null) {
    clearTimeout(logoutTimer);
    logoutTimer = null;
  }
  if (token === null) {
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    return;
  }
  window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  const expMs = jwtExpiresAt(token);
  if (expMs !== null) {
    const delay = Math.max(0, expMs - Date.now());
    logoutTimer = setTimeout(() => {
      logoutTimer = null;
      setToken(null);
    }, delay);
  }
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
  if (!raw) return null;
  const expMs = jwtExpiresAt(raw);
  if (expMs !== null && expMs <= Date.now()) {
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    return null;
  }
  return raw;
}

/** JWT atual no sessionStorage (não exposto como valor bruto fora do módulo). */
export function getClientAuthToken(): string | null {
  return getStoredToken();
}

export interface ClientSessionUser {
  id: string;
  email: string | null;
  telefone: string | null;
  role: string;
  fiscal_id?: string;
  tpa_id?: string;
}

/**
 * Resolve usuário para Header/Sidebar: cookie httpOnly primeiro; se falhar,
 * Bearer do sessionStorage (mesmo JWT do login) e por último claims mínimas.
 */
export async function fetchCurrentUser(): Promise<ClientSessionUser | null> {
  if (typeof window === "undefined") return null;

  const parseUser = (data: unknown): ClientSessionUser | null => {
    if (!data || typeof data !== "object" || !("id" in data) || !("role" in data)) {
      return null;
    }
    const u = data as ClientSessionUser;
    return u;
  };

  try {
    const r = await fetch("/api/auth/me", { credentials: "include", cache: "no-store" });
    if (r.ok) {
      return parseUser(await r.json());
    }
  } catch {
    /* noop */
  }

  const token = getStoredToken();
  if (!token) return null;

  try {
    const r2 = await fetch("/api/auth/me", {
      credentials: "include",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (r2.ok) {
      return parseUser(await r2.json());
    }
  } catch {
    /* noop */
  }

  const role = getRoleFromStoredToken();
  if (!role) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1] ?? "")) as { sub?: string };
    return {
      id: typeof payload.sub === "string" ? payload.sub : "",
      email: null,
      telefone: null,
      role,
    };
  } catch {
    return null;
  }
}

/** Role do JWT em sessionStorage (best-effort, mesmo payload que o middleware). */
export function getRoleFromStoredToken(): "FISCAL" | "DIRIGENTE" | "TPA" | null {
  const token = getStoredToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1] ?? "")) as { role?: string };
    const role = payload.role;
    if (role === "FISCAL" || role === "DIRIGENTE" || role === "TPA") return role;
  } catch {
    /* noop */
  }
  return null;
}

/** Repõe JWT no sessionStorage a partir do cookie httpOnly (refresh / nova aba). */
async function hydrateTokenFromCookie(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  if (getStoredToken()) return getStoredToken();
  try {
    const r = await fetch("/api/auth/token", { credentials: "include", cache: "no-store" });
    if (!r.ok) return null;
    const data = (await r.json()) as { access_token?: string };
    if (data.access_token) {
      setToken(data.access_token);
      return data.access_token;
    }
  } catch {
    /* noop */
  }
  return null;
}

// ---- Auth (cookie httpOnly, gerenciado server-side) -------------------------

/** Limpa token (sessionStorage + cookie httpOnly) e redireciona. */
export async function logout(): Promise<void> {
  if (typeof window === "undefined") return;
  setToken(null);
  try {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  } catch {
    /* noop */
  }
  window.location.href = "/login";
}

/** Faz login no proxy server-side, salva JWT em sessionStorage. */
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
  const data = (await r.json()) as { ok: boolean; role?: string; access_token?: string };
  // Proxy devolve access_token (além de ok/role). Salva em sessionStorage
  // p/ apiFetch usar via Authorization header.
  if (data.access_token) {
    setToken(data.access_token);
  }
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
 * Fetch com auth via Authorization header (Sprint B).
 *
 * Token vem do `sessionStorage` (setado pelo flow de login). Cookie
 * httpOnly continua válido p/ server components, mas não viaja
 * cross-domain no browser — então usamos Authorization header aqui.
 */
export async function apiFetch<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, noAuth = false, noRedirect = false, timeoutMs = 8000 } = opts;

  // C6: proxy same-origin /api/sindestiva/... (route handler público no App Router).
  const url = buildBffProxyUrl(path);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  // Token em sessionStorage → Authorization header (cross-domain safe).
  if (!noAuth) {
    let token = getStoredToken();
    if (!token) token = await hydrateTokenFromCookie();
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
      mode: "cors",
    });
  } catch (err) {
    clearTimeout(timer);
    const raw = err instanceof Error ? err.message : String(err);
    // Contexto para distinguir NXDOMAIN / CORS / timeout / conexão-recusada
    // na próxima ocorrência do sintoma (C4). Wrapper global captura este
    // console.error; não importar Sentry/Datadog diretamente aqui.
    const context = `[url=${url}][mode=cors]`;
    if (typeof console !== "undefined") {
      console.error("[apiFetch] network failure", { url, mode: "cors", raw });
    }
    throw new ApiError(0, `Falha de rede: ${raw} ${context}`);
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

export async function getRemanejamentos(
  filters?: { skip?: number; limit?: number; status?: string },
  catalogo?: RemanejamentoCatalogo,
): Promise<RemanejamentoItemResolved[]> {
  const params = new URLSearchParams();
  if (filters?.skip !== undefined) params.set("skip", String(filters.skip));
  if (filters?.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters?.status) params.set("status", filters.status);
  const q = params.toString() ? `?${params.toString()}` : "";
  const raw = await apiFetch<RemanejamentoItemResolved[] | RemanejamentoListResponseApi>(
    `/api/v1/remanejamentos${q}`,
  );
  return normalizeRemanejamentosList(raw, catalogo);
}

/**
 * `POST /api/v1/remanejamentos` — cria um remanejamento com o payload
 * `RemanejamentoBase` do Pydantic (sem `notify_pwa`/`ack_cct`).
 *
 * Retorna o `RemanejamentoRead` cru do backend; a UI que precisa de
 * nomes resolvidos chama `mapRemanejamentoRead` com um catálogo.
 */
export async function createRemanejamento(
  payload: unknown,
): Promise<RemanejamentoReadApi> {
  return apiFetch<RemanejamentoReadApi>("/api/v1/remanejamentos", {
    method: "POST",
    body: payload as Record<string, unknown> | undefined,
  });
}

/** `PATCH /api/v1/remanejamentos/{id}/aprovar` — PENDENTE → APROVADO. */
export async function aprovarRemanejamento(
  remanejamentoId: string,
  observacoes?: string | null,
): Promise<RemanejamentoReadApi> {
  return apiFetch<RemanejamentoReadApi>(
    `/api/v1/remanejamentos/${encodeURIComponent(remanejamentoId)}/aprovar`,
    {
      method: "PATCH",
      body: { observacoes: observacoes ?? null },
    },
  );
}

// ---- OGMO -----------------------------------------------------------------

export async function getOgmoNotificacoes(): Promise<OgmoNotificacao[]> {
  const raw = await apiFetch<OgmoNotificacaoApi[]>("/api/v1/ogmo/notificacoes");
  return raw.map(mapOgmoNotificacao);
}

/**
 * `POST /api/v1/remanejamentos/{id}/notificar-ogmo` — dispara Evolution
 * API (WhatsApp) + fallback SMTP/Resend + PDF anexo. Sem body.
 *
 * Equivale ao botão "Notificar OGMO" da tabela de remanejamentos
 * (HU002/CA03). Reaproveita `apiFetch` (mesma auth Bearer + cookie).
 */
export async function notifyOgmo(remanejamentoId: string): Promise<NotifyOgmoResponse> {
  return apiFetch<NotifyOgmoResponse>(
    `/api/v1/remanejamentos/${encodeURIComponent(remanejamentoId)}/notificar-ogmo`,
    { method: "POST" },
  );
}

/**
 * `POST /api/v1/ogmo/notificacoes/{remanejamento_id}/enviar` — alias
 * mantido para o botão "Reenviar" da Fila OGMO (HU005/RN06). Body:
 * `{ canal: "WHATSAPP" }`.
 *
 * Equivale ao botão "Reenviar" da `OgmoNotificacoesList`. Reaproveita
 * `apiFetch` (mesma auth Bearer + cookie).
 */
export async function resendOgmoNotificacao(remanejamentoId: string): Promise<NotifyOgmoResponse> {
  return apiFetch<NotifyOgmoResponse>(
    `/api/v1/ogmo/notificacoes/${encodeURIComponent(remanejamentoId)}/enviar`,
    { method: "POST", body: { canal: "WHATSAPP" } },
  );
}

// ---- Auditoria ------------------------------------------------------------

export async function getAuditEvents(
  limit = 100,
  entityType?: string,
): Promise<AuditEvent[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (entityType) params.set("entity_type", entityType);
  const raw = await apiFetch<AuditEventApi[]>(`/api/v1/auditoria/eventos?${params.toString()}`);
  return raw.map(mapAuditEvent);
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
  // Download via proxy (mesmo host) — sem isso, cookie cross-domain não viaja.
  // C6: o proxy já repassa content-disposition (route.ts:59-60), então o nome
  // do arquivo continua correto.
  const url = buildBffProxyUrl(`/api/v1/bi/export-pdf?periodo_dias=${periodoDias}`);
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

// ---- Gestão de usuários (DIRIGENTE) ---------------------------------------

export type AdminUserRole = "FISCAL" | "DIRIGENTE";
export type AdminUserStatus = "PENDENTE_ACEITE" | "ATIVO" | "BLOQUEADO" | "INATIVO";

export interface AdminUser {
  id: string;
  email: string | null;
  telefone: string | null;
  role: AdminUserRole;
  status: AdminUserStatus;
  nome_completo: string | null;
  cpf: string | null;
  matricula_sindicato: string | null;
  cargo: string | null;
  porto_codigo: string | null;
  turno_codigo: string | null;
  fiscal_status: string | null;
  data_inicio: string | null;
  data_inicio_mandato: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminUserListResponse {
  items: AdminUser[];
  total: number;
}

export interface AdminUserCreatePayload {
  email: string;
  telefone: string;
  password: string;
  role: AdminUserRole;
  status?: AdminUserStatus;
  cpf: string;
  nome_completo: string;
  matricula_sindicato: string;
  porto_codigo?: string;
  turno_codigo?: string;
  data_inicio?: string;
  cargo?: string;
  data_inicio_mandato?: string;
}

export type AdminUserUpdatePayload = Partial<
  Omit<AdminUserCreatePayload, "password">
> & { status?: AdminUserStatus };

export async function listAdminUsers(): Promise<AdminUserListResponse> {
  return apiFetch<AdminUserListResponse>("/api/v1/users");
}

export async function createAdminUser(payload: AdminUserCreatePayload): Promise<AdminUser> {
  return apiFetch<AdminUser>("/api/v1/users", { method: "POST", body: payload });
}

export async function updateAdminUser(
  userId: string,
  payload: AdminUserUpdatePayload,
): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/api/v1/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body: payload,
  });
}

// ---- Gestão de TPAs (DIRIGENTE) --------------------------------------------

export type TpaCadastroStatus = "ATIVO" | "AFASTADO" | "DESLIGADO" | "SUSPENSO";

export interface AdminTpaFuncaoMeta {
  id: string;
  codigo: string;
  nome: string;
  categoria: string;
}

export interface AdminTpa {
  id: string;
  user_id: string;
  email: string | null;
  telefone: string;
  user_status: AdminUserStatus;
  cpf: string;
  nome_completo: string;
  matricula_ogmo: string;
  funcao_base_id: string;
  funcao_codigo: string;
  funcao_nome: string;
  categoria: string;
  status_cadastro: TpaCadastroStatus;
  data_nascimento: string | null;
  data_admissao: string | null;
  data_desligamento: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminTpaListResponse {
  items: AdminTpa[];
  total: number;
}

export interface AdminTpaCreatePayload {
  cpf: string;
  nome_completo: string;
  matricula_ogmo: string;
  telefone: string;
  email?: string;
  funcao_base_id: string;
  status_cadastro?: TpaCadastroStatus;
  data_nascimento?: string;
  data_admissao?: string;
}

export type AdminTpaUpdatePayload = Partial<
  Omit<AdminTpaCreatePayload, "cpf">
> & {
  data_desligamento?: string;
};

export async function listAdminTpas(params?: {
  q?: string;
  status_cadastro?: TpaCadastroStatus;
  page?: number;
  page_size?: number;
}): Promise<AdminTpaListResponse> {
  const qs = new URLSearchParams();
  if (params?.q) qs.set("q", params.q);
  if (params?.status_cadastro) qs.set("status_cadastro", params.status_cadastro);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<AdminTpaListResponse>(`/api/v1/tpas${suffix}`);
}

export async function createAdminTpa(payload: AdminTpaCreatePayload): Promise<AdminTpa> {
  return apiFetch<AdminTpa>("/api/v1/tpas", { method: "POST", body: payload });
}

export async function updateAdminTpa(
  tpaId: string,
  payload: AdminTpaUpdatePayload,
): Promise<AdminTpa> {
  return apiFetch<AdminTpa>(`/api/v1/tpas/${encodeURIComponent(tpaId)}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function listTpaFuncoes(): Promise<AdminTpaFuncaoMeta[]> {
  return apiFetch<AdminTpaFuncaoMeta[]>("/api/v1/tpas/meta/funcoes");
}
