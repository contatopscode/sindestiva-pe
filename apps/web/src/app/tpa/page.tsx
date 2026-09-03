// =============================================================================
// SINDESTIVA-PE · /tpa — PWA do TPA (Início)
//
// Placeholder dentro do app web. O PWA real fica em apps/pwa/ (port 3001)
// com layout mobile-first, instalável e offline-first (Sprint 3).
//
// Aqui (apps/web) só a UI "espelho" para o Fiscal/Dirigente visualizar
// o que o TPA vê no celular — útil pra treinamento e suporte.
// =============================================================================

import type { ReactNode } from "react";
import Link from "next/link";
import type { Route } from "next";

const CARDS: Array<{
  href: string;
  icon: string;
  titulo: string;
  descricao: string;
  cor: string;
  disabled?: boolean;
}> = [
  {
    href: "/tpa/escala",
    icon: "📅",
    titulo: "Escala Hoje",
    descricao: "Veja sua escala do dia, cais e navio.",
    cor: "#2563eb",
  },
  {
    href: "/tpa/historico",
    icon: "📜",
    titulo: "Histórico",
    descricao: "Suas escalas dos últimos 30 dias.",
    cor: "#16a34a",
  },
  {
    href: "/tpa/perfil",
    icon: "👤",
    titulo: "Perfil",
    descricao: "Dados cadastrais e contato de emergência.",
    cor: "#ca8a04",
  },
  {
    href: "#",
    icon: "💬",
    titulo: "Falar com Fiscal",
    descricao: "Canal direto via WhatsApp (Sprint 3).",
    cor: "#db2777",
    disabled: true,
  },
];

export default function TpaInicioPage(): ReactNode {
  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">PWA · TPA</h1>
          <p className="section-subtitle">
            Visão do TPA no celular · Tela Início · 4 cards (Sprint 3)
          </p>
        </div>
      </div>

      <div className="rounded-md border border-[#e8a33d]/40 bg-[#e8a33d]/10 p-3 text-[12px] text-[#e8a33d]">
        ℹ️ Esta é uma visualização dentro do Centro de Comando. O PWA real (instalável)
        vive em <code className="font-mono">apps/pwa/</code> e roda na porta 3001.
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {CARDS.map((c) => {
          const inner = (
            <div
              className={`group relative h-full overflow-hidden rounded-lg border border-[#1e3a52] bg-[#0f2438] p-4 transition-colors ${
                c.disabled ? "cursor-not-allowed opacity-60" : "hover:border-[#d4a574] cursor-pointer"
              }`}
            >
              <div
                className="mb-3 grid h-10 w-10 place-items-center rounded-md text-xl"
                style={{ background: `${c.cor}22`, color: c.cor }}
              >
                {c.icon}
              </div>
              <h3 className="mb-1 text-[15px] font-bold text-[#e8eef4]">{c.titulo}</h3>
              <p className="text-[12px] text-[#94a8bd]">{c.descricao}</p>
              {c.disabled && (
                <span className="absolute right-2 top-2 rounded bg-[#e8a33d]/20 px-2 py-0.5 text-[9px] font-bold uppercase text-[#e8a33d]">
                  Em breve
                </span>
              )}
            </div>
          );

          return c.disabled ? (
            <div key={c.titulo}>{inner}</div>
          ) : (
            <Link key={c.titulo} href={c.href as Route}>{inner}</Link>
          );
        })}
      </div>
    </div>
  );
}
