"use client";

import Link from "next/link";
import type { Route } from "next";
import type { ReactNode } from "react";

export type PwaNavKey = "inicio" | "escala" | "historico" | "perfil" | "ogmo-recife";

const NAV_ITEMS: Array<{
  key: PwaNavKey;
  label: string;
  href?: Route;
}> = [
  { key: "inicio", label: "Início", href: "/" },
  { key: "escala", label: "Escala" },
  { key: "historico", label: "Histórico" },
  { key: "perfil", label: "Perfil" },
  { key: "ogmo-recife", label: "OGMO Recife", href: "/ogmo-recife" },
];

export function PwaBottomNav({ active }: { active: PwaNavKey }): ReactNode {
  return (
    <div className="phone-nav">
      {NAV_ITEMS.map((item) => {
        const className = `phone-nav-item${active === item.key ? " active" : ""}`;
        if (item.href) {
          return (
            <Link key={item.key} href={item.href} className={className}>
              {item.label}
            </Link>
          );
        }
        return (
          <button key={item.key} type="button" className={className} disabled>
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
