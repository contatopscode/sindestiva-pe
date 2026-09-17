/**
 * POST /api/auth/login
 *
 * Server-side proxy que chama a API, seta cookie httpOnly
 * `sindestiva_token` (domain por ambiente) e retorna {ok, role, access_token}.
 */
import { NextRequest, NextResponse } from "next/server";
import { API_URL } from "@/lib/api";
import { buildLoginSetCookieHeaders } from "@/lib/auth-cookie";

const API = API_URL;

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as {
    email?: string;
    password?: string;
  };
  const { email, password } = body;
  if (!email || !password) {
    return NextResponse.json(
      { error: "E-mail e senha são obrigatórios." },
      { status: 400 },
    );
  }

  let apiRes: Response;
  try {
    apiRes = await fetch(`${API}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });
  } catch (err) {
    return NextResponse.json(
      { error: `Falha de rede: ${(err as Error).message}` },
      { status: 502 },
    );
  }

  if (!apiRes.ok) {
    const detail = await apiRes.json().catch(() => ({ detail: "" }));
    const code = (detail && typeof detail === "object" && "detail" in detail)
      ? String((detail as { detail: unknown }).detail ?? "")
      : "";
    const msg = code.includes("INVALID_CREDENTIALS")
      ? "E-mail ou senha inválidos."
      : `Falha ao autenticar (${apiRes.status}).`;
    return NextResponse.json({ error: msg }, { status: apiRes.status });
  }

  const data = (await apiRes.json()) as {
    access_token: string;
    user: { role: string; id: string; email: string | null };
  };

  const host = req.headers.get("host") ?? "";
  const res = NextResponse.json({
    ok: true,
    role: data.user.role,
    access_token: data.access_token,
  });
  for (const cookieHeader of buildLoginSetCookieHeaders(data.access_token, host)) {
    res.headers.append("Set-Cookie", cookieHeader);
  }
  return res;
}
