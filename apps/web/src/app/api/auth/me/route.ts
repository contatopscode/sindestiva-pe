/**
 * GET /api/auth/me
 * Server-side proxy para /api/v1/auth/me — repassa cookie httpOnly.
 * Usado pelo Header do WEB pra mostrar user.role sem acesso direto à API.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.lousa.pscode.ia.br";

export async function GET() {
  const token = (await cookies()).get("sindestiva_token")?.value;
  if (!token) {
    return NextResponse.json({ error: "No session" }, { status: 401 });
  }

  const r = await fetch(`${API}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!r.ok) {
    return NextResponse.json({ error: "Invalid session" }, { status: r.status });
  }

  const data = await r.json();
  return NextResponse.json(data);
}
