// =============================================================================
// SINDESTIVA-PE · Cliente de /api/v1/navios (issue #15)
// Separado de `lib/api.ts` porque concentra a tradução erro→texto que a
// UI mostra. Regra: nada de status cru, "[object Object]" ou stacktrace
// chegando ao Fiscal.
// =============================================================================

import { ApiError, apiFetch } from "./api";
import type { NavioInput } from "./schemas/navio";

export interface Navio {
  id: string;
  nome: string;
  imo?: string | null;
  bandeira?: string | null;
  tipo_operacao?: string | null;
  created_at: string;
}

export interface NavioListResponse {
  items: Navio[];
  total: number;
  skip: number;
  limit: number;
}

/** `POST /api/v1/navios` — lança `ApiError` (com `code`) em falha. */
export async function criarNavio(input: NavioInput): Promise<Navio> {
  return apiFetch<Navio>("/api/v1/navios", { method: "POST", body: input, noRedirect: true });
}

/** `GET /api/v1/navios` — paginado, com busca opcional por nome/IMO. */
export async function listarNavios(params?: {
  q?: string;
  limit?: number;
}): Promise<NavioListResponse> {
  const qs = new URLSearchParams();
  if (params?.q) qs.set("q", params.q);
  qs.set("limit", String(params?.limit ?? 50));
  return apiFetch<NavioListResponse>(`/api/v1/navios?${qs.toString()}`);
}

// ---- Mapeamento de erro ---------------------------------------------------

const MSG_GENERICA = "Não foi possível salvar o navio. Tente novamente em instantes.";

/**
 * Um `detail` só é mostrado ao usuário se for texto de negócio.
 * Filtra stacktrace, serialização quebrada e mensagens gigantes.
 */
function ehAmigavel(texto: string | undefined): boolean {
  const s = (texto ?? "").trim();
  if (!s || s === "[object Object]" || s === "undefined") return false;
  if (s.length > 200) return false;
  return !/Traceback|\.py\b|\bat .+:\d+:\d+/.test(s);
}

/** Traduz qualquer falha de `criarNavio` numa frase acionável em PT-BR. */
export function mensagemErroNavio(err: unknown): string {
  if (!(err instanceof ApiError)) return MSG_GENERICA;

  // status 0 = o wrapper não conseguiu nem falar com a API.
  if (err.status === 0) {
    return "Sem conexão com o servidor. Verifique sua rede e tente novamente.";
  }

  if (err.status === 409) {
    if (err.code === "NAVIO_IMO_DUPLICADO" && ehAmigavel(err.detail)) return err.detail;
    return "Já existe um navio cadastrado com esse IMO. Verifique o número informado.";
  }

  if (err.status === 422 || err.status === 400) {
    return ehAmigavel(err.detail) && err.status === 422
      ? `Dados inválidos: ${err.detail}`
      : "Dados inválidos. Revise os campos destacados e tente novamente.";
  }

  // 5xx: mensagem do servidor nunca é exibida (pode ser stacktrace).
  if (err.status >= 500) return MSG_GENERICA;

  return ehAmigavel(err.detail) ? err.detail : MSG_GENERICA;
}
