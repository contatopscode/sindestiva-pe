// =============================================================================
// SINDESTIVA-PE · Header global
// Logo + título da seção + usuário + logout.
// =============================================================================

"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { logout, getCurrentUser } from "@/lib/api";
import { useEffect, useState } from "react";
import type { UserSession } from "@/lib/tipos";

const TITLES: Record<string, string> = {
  "/centro-comando": "Centro de Comando",
  "/remanejamentos": "Remanejamentos",
  "/remanejamentos/novo": "Novo Remanejamento",
  "/tpa": "PWA · TPA",
  "/tpa/escala": "PWA · Escala do Dia",
  "/tpa/historico": "PWA · Histórico",
  "/tpa/perfil": "PWA · Perfil",
  "/ogmo": "Fila de Notificação OGMO",
  "/auditoria": "Auditoria & Integridade",
};

export function Header(): ReactNode {
  const pathname = usePathname();
  const [user, setUser] = useState<UserSession | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setUser(getCurrentUser());
  }, []);

  const title = TITLES[pathname] ?? "SINDESTIVA-PE";
  const initials = (user?.nome ?? "P S")
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="header flex h-[60px] items-center gap-6 border-b border-[#1e3a52] bg-[#0a1929] px-6 sticky top-0 z-50">
      {/* Brand */}
      <div className="flex items-center gap-3 min-w-[216px]">
        <div className="grid h-9 w-9 place-items-center rounded-md bg-gradient-to-br from-[#d4a574] to-[#b8884f] text-sm font-extrabold text-[#0a1929]">
          S
        </div>
        <div className="leading-tight">
          <div className="text-sm font-bold tracking-wide text-[#e8eef4]">SINDESTIVA-PE</div>
          <div className="text-[11px] uppercase tracking-wider text-[#94a8bd]">{title}</div>
        </div>
      </div>

      {/* DEMO badge — remover quando Sprint 1 autenticar */}
      <div className="rounded bg-[#d4a574]/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#d4a574]">
        Demo · Sprint 4 UI
      </div>

      <div className="flex-1" />

      {/* User + logout */}
      {mounted && user && (
        <div className="flex items-center gap-3">
          <div className="text-right leading-tight">
            <div className="text-[12px] font-semibold text-[#e8eef4]">{user.nome}</div>
            <div className="text-[10px] uppercase tracking-wider text-[#94a8bd]">
              {user.role}
            </div>
          </div>
          <div className="grid h-9 w-9 place-items-center rounded-full bg-[#163554] text-[12px] font-bold text-[#e8eef4]">
            {initials}
          </div>
          <button
            onClick={() => logout()}
            className="rounded border border-[#2a5070] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-[#94a8bd] transition-colors hover:border-[#d4a574] hover:text-[#d4a574]"
            aria-label="Sair"
          >
            Sair
          </button>
        </div>
      )}
    </header>
  );
}
