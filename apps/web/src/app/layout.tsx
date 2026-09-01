// =============================================================================
// SINDESTIVA-PE · Layout raiz do Centro de Comando (apps/web)
//
// Estrutura: grid com header (60px) + sidebar (240px) + main (1fr).
// Mantém as classes CSS existentes em globals.css (.app, .header, .sidebar,
// .main) para preservar 100% a identidade visual do protótipo.
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

export default function RootLayout({ children }: { children: ReactNode }) {
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
