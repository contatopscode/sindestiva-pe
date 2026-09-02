// =============================================================================
// SINDESTIVA-PE · Sidebar (5 grupos do plano v1.0)
//
// Conforme SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md §2 (Centro de
// Comando) + protótipo SINDESTIVA-PE-PROTOTIPO.html linhas 1246+.
//
// Itens agrupados por domínio. Marca "DEMO" no header da lousa enquanto
// não tivermos autenticação real (Sprint 1).
//
// TODO Sprint 1: mover `activeHref` para `usePathname()` (Next.js hooks).
// TODO Sprint 5: habilitar item "OGMO" (depende de T5-08 — token fixo).
// =============================================================================

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export interface SidebarItem {
  href: string;
  label: string;
  icon?: string;
  badge?: string;
  disabled?: boolean;
  /** Quando true, abre em nova aba (ex: OGMO read-only). */
  external?: boolean;
}

export interface SidebarGroup {
  title: string;
  items: SidebarItem[];
}

const GROUPS: SidebarGroup[] = [
  {
    title: "Análise",
    items: [
      { href: "/centro-comando", label: "Lousa Espelhada", icon: "📋" },
      { href: "/remanejamentos", label: "Remanejamentos", icon: "🔄" },
      { href: "/ogmo", label: "Fila OGMO", icon: "📡" },
      { href: "/auditoria", label: "Auditoria", icon: "🔍" },
    ],
  },
  {
    title: "TPA",
    items: [
      { href: "/tpa", label: "PWA (Início)", icon: "👷" },
    ],
  },
  {
    title: "Plataforma",
    items: [
      { href: "/bi", label: "BI & Dashboards", icon: "📊" },
    ],
  },
  {
    title: "Sistema",
    items: [
      { href: "#", label: "Manual (em breve)", icon: "📖", disabled: true },
    ],
  },
];

export function Sidebar(): ReactNode {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-[240px] flex-col border-r border-[#1e3a52] bg-[#0a1929] py-4 overflow-y-auto">
      {GROUPS.map((group) => (
        <div key={group.title} className="mb-6">
          <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-[#5f7a92]">
            {group.title}
          </div>
          {group.items.map((item) => {
            const active = !item.disabled && pathname === item.href;
            const base =
              "mx-2 mb-1 flex items-center gap-3 rounded-md px-3 py-2 text-[13px] font-medium transition-colors";
            const state = item.disabled
              ? "text-[#3a4d63] cursor-not-allowed"
              : active
                ? "bg-[#122e47] text-[#e8eef4] shadow-[inset_3px_0_0_#d4a574] cursor-pointer"
                : "text-[#94a8bd] hover:bg-[#163554] hover:text-[#e8eef4] cursor-pointer";

            const content = (
              <>
                {item.icon && <span className="text-base leading-none">{item.icon}</span>}
                <span className="flex-1 truncate">{item.label}</span>
                {item.badge && (
                  <span className="rounded bg-[#d4a574]/20 px-1.5 py-0.5 text-[9px] font-bold uppercase text-[#d4a574]">
                    {item.badge}
                  </span>
                )}
              </>
            );

            if (item.disabled || item.external) {
              return (
                <div key={item.href + item.label} className={`${base} ${state}`}>
                  {content}
                </div>
              );
            }
            return (
              <Link key={item.href} href={item.href} className={`${base} ${state}`}>
                {content}
              </Link>
            );
          })}
        </div>
      ))}

      <div className="mt-auto px-3 pt-4 border-t border-[#1e3a52] text-[10px] text-[#5f7a92]">
        <div className="font-semibold text-[#94a8bd]">SINDESTIVA-PE</div>
        <div>v0.1.0 · Sprint 4 UI</div>
      </div>
    </aside>
  );
}
