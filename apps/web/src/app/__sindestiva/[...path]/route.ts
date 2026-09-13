/**
 * Catch-all proxy: /__sindestiva/* → API_URL/<caller-path>
 *
 * O caller (`apiFetch` em `@/lib/api`) já envia o path COMPLETO, incluindo
 * o prefixo `/api/v1/`. Este handler apenas concatena `API_URL + / + path`
 * — NÃO adiciona prefixo próprio, para não duplicar `/api/v1/api/v1/...`.
 *
 * Por que isso existe:
 *   O cookie `sindestiva_token` é domain-scoped ao host
 *   `web.lousa.pscode.ia.br`. Fazer o browser chamar API diretamente
 *   (`api.lousa...`) não envia cookie (3rd-party restriction). Solução:
 *   front chama `/__sindestiva/...` no mesmo host (Vercel) e este
 *   handler repassa pra API server-side, copiando o cookie.
 *
 *   (Tentamos usar `rewrites()` no next.config.mjs mas a Vercel tava
 *   mostrando 404; route handler é mais confiável.)
 *
 * Implementação: usa `route.ts` do App Router + `[...path]/route.ts`.
 * Suporta GET, POST, PUT, PATCH, DELETE. Stream do body preservado.
 */
import { cookies } from "next/headers";
import type { NextRequest } from "next/server";
import { API_URL } from "@/lib/api";

const API = API_URL;

async function proxy(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await ctx.params;
  const fullPath = path.join("/");
  // Caller já envia o prefixo `/api/v1/...` completo — não duplicar aqui.
  // Apenas junta `API_URL + / + path-capturado + query-string`.
  const url = `${API}/${fullPath}${req.nextUrl.search}`;
  const cookieStore = await cookies();
  const tokenCookie = cookieStore.get("sindestiva_token")?.value;
  const allCookies = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  const init: RequestInit = {
    method: req.method,
    headers: {
      "Content-Type": req.headers.get("content-type") ?? "application/json",
      ...(tokenCookie ? { Authorization: `Bearer ${tokenCookie}` } : {}),
      ...(allCookies ? { Cookie: allCookies } : {}),
    },
    // Não propagar body se GET/HEAD.
    ...(req.method === "GET" || req.method === "HEAD"
      ? {}
      : { body: req.body ?? undefined }),
    cache: "no-store",
  };

  const upstream = await fetch(url, init);

  // Repassa body + status + headers relevantes (CORS!).
  const resHeaders = new Headers();
  // Resposta: repassa content-type + cors.
  const ct = upstream.headers.get("content-type");
  if (ct) resHeaders.set("content-type", ct);
  const ce = upstream.headers.get("content-encoding");
  if (ce) resHeaders.set("content-encoding", ce);
  const cd = upstream.headers.get("content-disposition");
  if (cd) resHeaders.set("content-disposition", cd);
  // CORS p/ browser poder ler resposta cross-domain.
  const origin = req.headers.get("origin") ?? `https://web.lousa.pscode.ia.br`;
  resHeaders.set("Access-Control-Allow-Origin", origin);
  resHeaders.set("Access-Control-Allow-Credentials", "true");
  resHeaders.set("Vary", "Origin");

  // Stream o body pra baixo latência.
  return new Response(upstream.body, {
    status: upstream.status,
    headers: resHeaders,
  });
}

function handler(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  return proxy(req, ctx);
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const HEAD = handler;
export const OPTIONS = handler;

// Re-exporta o tipo p/ inferência em runtime.
export type ProxyFn = typeof proxy;
