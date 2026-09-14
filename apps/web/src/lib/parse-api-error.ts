import { ApiError } from "./api";

function formatDetailValue(detail: unknown): string {
  if (detail === null || detail === undefined) {
    return "Erro desconhecido";
  }
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const row = item as { loc?: unknown; msg?: unknown; message?: unknown };
          const loc = Array.isArray(row.loc) ? row.loc.join(".") : "";
          const msg =
            typeof row.msg === "string"
              ? row.msg
              : typeof row.message === "string"
                ? row.message
                : JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join("; ");
  }
  if (typeof detail === "object") {
    const row = detail as { code?: unknown; message?: unknown };
    if (typeof row.message === "string") {
      if (typeof row.code === "string" && row.code) {
        return `${row.message} (${row.code})`;
      }
      return row.message;
    }
    return JSON.stringify(detail);
  }
  return String(detail);
}

/** Normaliza `ApiError.detail` (string JSON ou texto) para mensagem legível. */
export function parseApiError(err: unknown): string {
  if (err instanceof ApiError) {
    const raw = err.detail.trim();
    if (!raw) return `Erro HTTP ${err.status}`;
    try {
      return formatDetailValue(JSON.parse(raw) as unknown);
    } catch {
      return raw;
    }
  }
  return err instanceof Error ? err.message : "Erro desconhecido";
}
