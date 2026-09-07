/**
 * SINDESTIVA-PE · Login + server-side auth (Sprint B).
 *
 * Estratégia: NÃO usamos NextAuth.js (overhead grande p/ 3 roles simples).
 * Em vez disso, server-side fetch com cookie httpOnly:
 *
 *   - Login (server action): valida e-mail+senha via API → seta cookie
 *     `sindestiva_token` (httpOnly, secure, sameSite=Lax, maxAge=8h).
 *   - Middleware: checa cookie em rotas /centro-comando, /bi, /ogmo,
 *     /auditoria, /remanejamentos, /tpa.
 *   - apiFetch (cliente): envia `credentials: 'include'` — cookie vai
 *     automaticamente.
 *
 * Vantagens:
 *   - Sem dependência extra (já temos `next-auth` em deps, mas é
 *     overkill — optamos por não usar agora, Sprint D pode migrar).
 *   - JWT em cookie httpOnly = imune a XSS.
 *   - Mesmo cookie serve para API de prod (cross-origin via CORS).
 */
import { cookies } from "next/headers";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.lousa.pscode.ia.br";
const COOKIE_NAME = "sindestiva_token";
const COOKIE_MAX_AGE = 8 * 60 * 60;  // 8h, mesmo do JWT

export type Role = "FISCAL" | "DIRIGENTE" | "TPA";

export interface SessionUser {
  id: string;
  email: string | null;
  telefone: string | null;
  role: Role;
  status: string;
  /** Preenchido quando role=FISCAL */
  fiscal_id?: string;
  /** Preenchido quando role=TPA */
  tpa_id?: string;
}

export interface LoginResult {
  ok: boolean;
  error?: string;
}

/** Login server-side: chama API e seta cookie httpOnly. */
export async function loginAction(
  email: string,
  password: string,
): Promise<LoginResult> {
  try {
    const r = await fetch(`${API}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });

    if (!r.ok) {
      if (r.status === 401 || r.status === 422) {
        return { ok: false, error: "Email ou senha inválidos." };
      }
      return { ok: false, error: `Erro ${r.status} ao autenticar.` };
    }

    const data = (await r.json()) as {
      access_token: string;
      user: SessionUser;
    };

    // Seta cookie httpOnly — imune a XSS, presente em todas as requests.
    (await cookies()).set({
      name: COOKIE_NAME,
      value: data.access_token,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: COOKIE_MAX_AGE,
    });

    return { ok: true };
  } catch (err) {
    return { ok: false, error: `Falha de rede: ${(err as Error).message}` };
  }
}

/** Logout: remove cookie. */
export async function logoutAction(): Promise<void> {
  (await cookies()).delete(COOKIE_NAME);
}

/** Lê JWT do cookie e busca user via API. Retorna null se inválido. */
export async function getSession(): Promise<SessionUser | null> {
  const c = (await cookies()).get(COOKIE_NAME);
  if (!c?.value) return null;

  try {
    const r = await fetch(`${API}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${c.value}` },
      cache: "no-store",
    });
    if (!r.ok) return null;
    return (await r.json()) as SessionUser;
  } catch {
    return null;
  }
}

/** Lê só o JWT (para usar em server components que fazem fetch direto). */
export async function getToken(): Promise<string | null> {
  const c = (await cookies()).get(COOKIE_NAME);
  return c?.value ?? null;
}

/** Gateway de role — usado em server components / page.tsx. */
export async function requireRole(
  allowed: Role[],
): Promise<SessionUser> {
  const user = await getSession();
  if (!user) {
    throw new Error("UNAUTHORIZED");
  }
  if (!allowed.includes(user.role)) {
    throw new Error("FORBIDDEN");
  }
  return user;
}

export const COOKIE_NAME_EXPORT = COOKIE_NAME;
