/**
 * SINDESTIVA-PE · Middleware de gate (Sprint B).
 *
 * Protege rotas com base no cookie httpOnly `sindestiva_token`.
 * Se ausente → redireciona p/ /login com `next=` original.
 *
 * Decodificação JWT inline via base64 (sem libs externas — middleware
 * roda no Edge runtime, queremos footprint mínimo). A ASSINATURA é
 * revalidada no server component (`getSession()` chama /me na API).
 *
 * IMPORTANTE: a checagem aqui é best-effort p/ UX (decide redirect).
 * A validação real é server-side no `getSession()`.
 */
import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "sindestiva_token";

const PUBLIC_ROUTES = new Set(["/login"]);

const ROLE_RULES: Array<{ prefix: string; allowed: string[] }> = [
  { prefix: "/bi", allowed: ["DIRIGENTE"] },
  { prefix: "/centro-comando", allowed: ["FISCAL", "DIRIGENTE", "TPA"] },
  { prefix: "/remanejamentos", allowed: ["FISCAL", "DIRIGENTE"] },
  { prefix: "/ogmo", allowed: ["FISCAL", "DIRIGENTE"] },
  { prefix: "/auditoria", allowed: ["FISCAL", "DIRIGENTE"] },
  { prefix: "/tpa", allowed: ["FISCAL", "DIRIGENTE", "TPA"] },
];

function matchRule(path: string) {
  return ROLE_RULES.find(
    (r) => path === r.prefix || path.startsWith(r.prefix + "/"),
  );
}

/** Decodifica payload JWT HS256 (sem validar assinatura — best-effort). */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    // base64url → base64 → utf-8 JSON
    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const json = atob(padded);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api/") ||
    PUBLIC_ROUTES.has(pathname) ||
    pathname === "/favicon.ico"
  ) {
    return NextResponse.next();
  }

  const rule = matchRule(pathname);
  if (!rule) {
    return NextResponse.next();
  }

  const token = req.cookies.get(COOKIE_NAME)?.value;
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // Decodifica JWT só p/ extrair role (otimização p/ UX).
  // Validação real é server-side em getSession() via API.
  const payload = decodeJwtPayload(token);
  const exp = typeof payload?.exp === "number" ? payload.exp : 0;
  const role = String(payload?.role || "");

  // Token expirado? Manda pra login.
  if (!exp || exp * 1000 < Date.now()) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    url.searchParams.set("reason", "expired");
    return NextResponse.redirect(url);
  }

  if (!rule.allowed.includes(role)) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("error", "forbidden");
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

// Config vazio — Next.js 15 usa default (todas as rotas exceto _next/*).
// Fazemos o filtro manualmente dentro da função middleware() para evitar
// o erro de tipo `string is not assignable to RouteImpl<string>`.
// Workaround: matcher vazio = Next aplica em todas, e o filtro interno
// cuida do resto. Mais simples e compatível.
export const config = {
  matcher: "/((?!_next/static|_next/image|favicon.ico).*)",
} as never;
