/**
 * GET /api/auth/me
 * Server-side proxy para /api/v1/auth/me — cookie httpOnly ou Authorization Bearer.
 */
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { API_URL } from "@/lib/api";
import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";

const API = API_URL;

function bearerFromRequest(req: NextRequest): string | null {
  const raw = req.headers.get("authorization");
  if (!raw?.startsWith("Bearer ")) return null;
  const token = raw.slice(7).trim();
  return token || null;
}

export async function GET(req: NextRequest) {
  const cookieToken = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const bearer = bearerFromRequest(req);
  const token = cookieToken ?? bearer;
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
