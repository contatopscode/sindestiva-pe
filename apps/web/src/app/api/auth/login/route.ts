/**
 * POST /api/auth/login
 *
 * Server-side proxy que chama a API de prod, seta cookie httpOnly
 * `sindestiva_token` e retorna {ok, role, access_token}.
 */
import { NextRequest, NextResponse } from "next/server";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.lousa.pscode.ia.br";
const COOKIE_NAME = "sindestiva_token";
const COOKIE_MAX_AGE = 8 * 60 * 60;

function buildCookieValue(data: { access_token: string }): string {
  // Set-Cookie cru (Next.js cookies().set() pode ignorar campos extras
  // como `domain` em algumas versões — montar na mão dá controle total).
  const parts = [
    `${COOKIE_NAME}=${data.access_token}`,
    `Path=/`,
    `Max-Age=${COOKIE_MAX_AGE}`,
    `HttpOnly`,
    `SameSite=Lax`,
  ];
  if (process.env.NODE_ENV === "production") {
    parts.push("Secure");
    parts.push("Domain=.pscode.ia.br"); // compartilha entre web.lousa.pscode.ia.br e api.lousa.pscode.ia.br
  }
  return parts.join("; ");
}

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

  // Constrói Set-Cookie com `Domain=.pscode.ia.br` (cookies() ignorado).
  const res = NextResponse.json({
    ok: true,
    role: data.user.role,
    access_token: data.access_token,  // client-side também usa (Authorization header)
  });
  res.headers.append(
    "Set-Cookie",
    buildCookieValue({ access_token: data.access_token }),
  );
  return res;
}
