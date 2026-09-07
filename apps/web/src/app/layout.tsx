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
  // Gate server-side (substitui middleware.ts — incompatível com Next 15.5+).
  // Para o gate em /login (rota pública), criamos apps/web/src/app/login/layout.tsx
  // que NÃO chama este layout. O gate aqui só bloqueia rotas autenticadas.
  const { cookies, headers } = await import("next/headers");
  const cookieStore = await cookies();
  const hdrs = await headers();
  const token = cookieStore.get("sindestiva_token")?.value;
  // `next-url` header tem a rota original (sem query).
  const originalPath = hdrs.get("x-invoke-path") ?? hdrs.get("next-url") ?? "";

  // Pula gate em /login (rota pública).
  // Se chegou sem cookie, redireciona pro /login com next=pathname.
  if (!token) {
    if (originalPath.startsWith("/login")) {
      // Deixa renderizar normal (página /login)
    } else {
      const nextParam = originalPath ? `?next=${encodeURIComponent(originalPath)}` : "?next=/centro-comando";
      redirect(`/login${nextParam}`);
    }
  }

  // Valida token chamando /me
  if (token) {
    try {
      const r = await fetch(`${API}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (!r.ok) {
        if (originalPath.startsWith("/login")) {
          // /login renderiza mesmo com token inválido (logout)
        } else {
          redirect(`/login?next=${encodeURIComponent(originalPath || "/centro-comando")}&reason=expired`);
        }
      }
    } catch {
      // Falha de rede: deixa passar
    }
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
