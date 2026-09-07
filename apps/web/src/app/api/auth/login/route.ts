/**
 * POST /api/auth/login
 *
 * Server-side proxy que chama a API de prod, seta cookie httpOnly
 * `sindestiva_token` e retorna {ok, role}.
 */
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.lousa.pscode.ia.br";
const COOKIE_NAME = "sindestiva_token";
const COOKIE_MAX_AGE = 8 * 60 * 60;

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

  (await cookies()).set({
    name: COOKIE_NAME,
    value: data.access_token,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: COOKIE_MAX_AGE,
  });

  return NextResponse.json({ ok: true, role: data.user.role });
}
