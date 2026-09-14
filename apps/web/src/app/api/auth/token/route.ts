/**
 * GET /api/auth/token
 *
 * Expõe o JWT do cookie httpOnly ao client (same-origin) para
 * sessionStorage — necessário p/ Authorization em chamadas cross-origin à API.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";

const COOKIE_NAME = AUTH_COOKIE_NAME;

export async function GET() {
  const token = (await cookies()).get(COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ error: "No session" }, { status: 401 });
  }
  return NextResponse.json({ access_token: token });
}
