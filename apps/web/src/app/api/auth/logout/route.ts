/**
 * POST /api/auth/logout
 * Remove o cookie httpOnly.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST() {
  (await cookies()).delete("sindestiva_token");
  return NextResponse.json({ ok: true });
}
