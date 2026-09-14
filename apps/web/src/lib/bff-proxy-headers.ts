/**
 * Helpers do catch-all BFF (`app/api/sindestiva/[...path]/route.ts`).
 * Extraídos para testes unitários (vitest).
 */

/** Headers de transferência que não devem ser repassados após decode do body no Node. */
const STRIP_FROM_UPSTREAM = new Set([
  "content-encoding",
  "content-length",
  "transfer-encoding",
]);

/**
 * Monta headers da resposta do proxy a partir do upstream.
 *
 * Node/undici `fetch` descomprime gzip/deflate automaticamente — o body já é
 * JSON/texto em claro. Repassar `Content-Encoding: gzip` faz o browser tentar
 * descomprimir de novo e quebra `res.json()` ("Failed to fetch").
 */
export function buildProxyResponseHeaders(
  upstream: Headers,
  requestOrigin: string | null,
): Headers {
  const out = new Headers();
  upstream.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (STRIP_FROM_UPSTREAM.has(lower)) return;
    out.set(key, value);
  });

  // Same-origin BFF: sem Origin na request → não emitir CORS (evita Allow-Origin
  // hardcoded de prod quando o caller é o próprio web.hom).
  if (requestOrigin) {
    out.set("Access-Control-Allow-Origin", requestOrigin);
    out.set("Access-Control-Allow-Credentials", "true");
    out.set("Vary", "Origin");
  }

  return out;
}

/**
 * Authorization para o upstream: preferir header do cliente (sessionStorage/Bearer),
 * senão cookie httpOnly `sindestiva_token`.
 */
export function resolveUpstreamAuthorization(
  incomingAuthorization: string | null,
  cookieToken: string | undefined,
): string | undefined {
  const trimmed = incomingAuthorization?.trim();
  if (trimmed) return trimmed;
  if (cookieToken) return `Bearer ${cookieToken}`;
  return undefined;
}
