// =============================================================================
// SINDESTIVA-PE · Layout raiz do Centro de Comando (apps/web)
//
// Sprint B: este layout SÓ é renderizado para rotas autenticadas.
// Rotas públicas (/login) têm layout próprio.
//
// Gate: checa cookie httpOnly `sindestiva_token` e redireciona pra
// `/login?next=...` se ausente/inválido. Mais simples que middleware
// (sem problema de tipo com Next 15.5) e cobre 100% das rotas.
// =============================================================================

import type { Metadata } from "next";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { Sidebar } from "./_components/Sidebar";
import { Header } from "./_components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lousa Digital · SINDESTIVA-PE",
  description: "Centro de Comando do SINDESTIVA-PE — Lousa Espelhada, Remanejamentos, OGMO, Auditoria.",
};

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.lousa.pscode.ia.br";

export default async function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  // Server-side auth gate (Sprint B — Sprint 1 colocava em middleware mas
  // dava erro de tipo RouteImpl<string> no Next 15.5+).
  // Fazemos aqui, antes do HTML ser enviado.
  // Validação REAL é server-side (chama /api/v1/auth/me).
  const { cookies } = await import("next/headers");
  const cookieStore = await cookies();
  const token = cookieStore.get("sindestiva_token")?.value;

  if (!token) {
    redirect("/login?next=/centro-comando");
  }

  // Valida token chamando /me — bypassa cache
  try {
    const r = await fetch(`${API}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!r.ok) {
      redirect("/login?next=/centro-comando&reason=expired");
    }
  } catch {
    // Falha de rede: deixa passar (cliente vai detectar 401 nos fetches)
  }

  return (
    <html lang="pt-BR">
      <body>
        <div className="app">
          <Header />
          <Sidebar />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
