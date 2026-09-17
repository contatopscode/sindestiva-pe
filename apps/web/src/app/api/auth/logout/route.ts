/**
 * POST /api/auth/logout
 * Remove cookie httpOnly do host e expira legado Domain=.pscode.ia.br.
 */
import { NextRequest, NextResponse } from "next/server";
import { buildLogoutSetCookieHeaders } from "@/lib/auth-cookie";

export async function POST(req: NextRequest) {
  const host = req.headers.get("host") ?? "";
  const res = NextResponse.json({ ok: true });
  for (const cookieHeader of buildLogoutSetCookieHeaders(host)) {
    res.headers.append("Set-Cookie", cookieHeader);
  }
  return res;
}
