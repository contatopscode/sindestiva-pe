// Resolução da base URL da API — seguro para server (route handlers) e client.

const DEFAULT_API_URL = "https://api.lousa.pscode.ia.br";

/**
 * Resolve a base URL da API a partir de NEXT_PUBLIC_API_URL.
 *
 * - Em produção: se a env não estiver setada (ou for string vazia),
 *   LANÇA erro. Falha alto no carregamento do módulo é preferível a
 *   bundle rodando com fallback NXDOMAIN.
 * - Em dev: aceita fallback silencioso para não atrapalhar DX local.
 */
export function resolveApiUrl(): string {
  const fromEnv =
    typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_URL : undefined;
  if (fromEnv && fromEnv.trim()) return fromEnv.replace(/\/$/, "");
  if (typeof process !== "undefined" && process.env.NODE_ENV === "production") {
    throw new Error(
      "NEXT_PUBLIC_API_URL não definida em produção. " +
        "Configure a env na plataforma de deploy e faça rebuild.",
    );
  }
  return DEFAULT_API_URL; // dev only
}

/** Constante de dev — única ocorrência de runtime permitida (CI C3). */
export const DEFAULT_API_URL_DEV = DEFAULT_API_URL;
