// Resolução da base URL da API — seguro para server (route handlers) e client.

const DEFAULT_API_URL = "https://api.lousa.pscode.ia.br";

/**
 * Resolve a base URL da API a partir de NEXT_PUBLIC_API_URL.
 *
 * - Se a env estiver setada (build/runtime Vercel, Coolify, etc.), usa-a.
 * - Caso contrário, cai no DEFAULT canônico (`api.lousa.pscode.ia.br`) —
 *   mesmo padrão do docker-compose. Evita falha de `next build` quando o
 *   projeto Vercel ainda não tem a env marcada como build-time.
 */
export function resolveApiUrl(): string {
  const fromEnv =
    typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_URL : undefined;
  if (fromEnv && fromEnv.trim()) return fromEnv.replace(/\/$/, "");
  return DEFAULT_API_URL.replace(/\/$/, "");
}

/** Constante de dev — única ocorrência de runtime permitida (CI C3). */
export const DEFAULT_API_URL_DEV = DEFAULT_API_URL;
