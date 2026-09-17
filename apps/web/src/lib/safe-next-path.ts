const DEFAULT_AFTER_LOGIN = "/centro-comando";

/**
 * Restringe `next` da query de login a caminhos same-origin (path relativo).
 * Bloqueia open redirect (`//`, `https:`, backslash, etc.).
 */
export function sanitizeNextPath(
  raw: string | null | undefined,
  fallback = DEFAULT_AFTER_LOGIN,
): string {
  if (raw == null || typeof raw !== "string") return fallback;

  const trimmed = raw.trim();
  if (!trimmed) return fallback;

  if (!trimmed.startsWith("/") || trimmed.startsWith("//")) return fallback;
  if (trimmed.includes("\\") || trimmed.includes("\0")) return fallback;
  if (trimmed.includes("://") || trimmed.includes("@")) return fallback;

  return trimmed;
}

export { DEFAULT_AFTER_LOGIN };
