// =============================================================================
// SINDESTIVA-PE · Layout raiz do Centro de Comando (apps/web)
//
// Estrutura: grid com header (60px) + sidebar (240px) + main (1fr).
//
// Sprint B — gate de auth:
//   Estratégia mínima viável — o gate server-side no layout.tsx
//   quebrou por causa do redirect loop em /login. Solução:
//     - Não bloqueia aqui (RootLayout renderiza sempre).
//     - Header.tsx busca /api/auth/me (cookie) → user aparece só se logado.
//     - Client side: cada `apiFetch` faz `credentials: 'include'`, 401 →
//       redireciona pra /login (já implementado em lib/api.ts).
//   Trade-off aceitável: a página renderiza antes de checar auth,
//   mas o conteúdo protegido (BI, OGMO, etc.) só aparece se autenticado
//   (porque cada fetch individual retorna 401 → mensagem de erro na UI).
//
// Próxima sprint (B+): migrar para um auth provider tipo NextAuth real,
//   que dá SSR-aware redirects sem loop.
//
// =============================================================================

import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Sidebar } from "./_components/Sidebar";
import { Header } from "./_components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lousa Digital · SINDESTIVA-PE",
  description: "Centro de Comando do SINDESTIVA-PE — Lousa Espelhada, Remanejamentos, OGMO, Auditoria.",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
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
