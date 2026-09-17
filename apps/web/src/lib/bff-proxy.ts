/**
 * Same-origin BFF proxy prefix (App Router route em `app/api/sindestiva/[...path]`).
 *
 * NÃO usar pasta sob `app/` cujo nome começa com `_` — Next.js trata como
 * private folder e não registra a rota (regressão FSW-001 / homolog 2026).
 */
export const BFF_PROXY_PREFIX = "/api/sindestiva";

/**
 * Monta URL same-origin para o catch-all proxy.
 * `apiPath` deve incluir o prefixo `/api/v1/...` (repassado intacto ao upstream).
 */
export function buildBffProxyUrl(apiPath: string): string {
  const normalized = apiPath.startsWith("/") ? apiPath : `/${apiPath}`;
  return `${BFF_PROXY_PREFIX}${normalized}`;
}
