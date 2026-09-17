/**
 * Catch-all proxy: /api/sindestiva/* → API_URL/<caller-path>
 *
 * O caller (`apiFetch` em `@/lib/api`) já envia o path COMPLETO, incluindo
 * o prefixo `/api/v1/`. Este handler apenas concatena `API_URL + / + path`
 * — NÃO adiciona prefixo próprio, para não duplicar `/api/v1/api/v1/...`.
 *
 * Por que isso existe:
 *   O cookie `sindestiva_token` é domain-scoped ao host
 *   `web.lousa.pscode.ia.br`. Fazer o browser chamar API diretamente
 *   (`api.lousa...`) não envia cookie (3rd-party restriction). Solução:
 *   front chama `/api/sindestiva/...` no mesmo host e este
 *   handler repassa pra API server-side, copiando o cookie.
 */
import { cookies } from "next/headers";
import type { NextRequest } from "next/server";
import {
  buildProxyResponseHeaders,
  proxyMethodOmitsBody,
  resolveUpstreamAuthorization,
} from "@/lib/bff-proxy-headers";
import { resolveApiUrl } from "@/lib/api-url";
import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";

const API = resolveApiUrl();

async function proxy(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await ctx.params;
  const fullPath = path.join("/");
  const url = `${API}/${fullPath}${req.nextUrl.search}`;
  const cookieStore = await cookies();
  const tokenCookie = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const allCookies = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  const authorization = resolveUpstreamAuthorization(
    req.headers.get("authorization"),
    tokenCookie,
  );

  let body: ArrayBuffer | undefined;
  if (!proxyMethodOmitsBody(req.method)) {
    body = await req.arrayBuffer();
  }

  const init: RequestInit = {
    method: req.method,
    headers: {
      "Content-Type": req.headers.get("content-type") ?? "application/json",
      ...(authorization ? { Authorization: authorization } : {}),
      ...(allCookies ? { Cookie: allCookies } : {}),
    },
    ...(body !== undefined ? { body } : {}),
    cache: "no-store",
  };

  try {
    const upstream = await fetch(url, init);

    const resHeaders = buildProxyResponseHeaders(
      upstream.headers,
      req.headers.get("origin"),
    );

    return new Response(upstream.body, {
      status: upstream.status,
      headers: resHeaders,
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Falha ao contactar a API upstream";
    return Response.json(
      {
        error: {
          code: "BFF_PROXY_ERROR",
          message,
        },
      },
      { status: 500 },
    );
  }
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
