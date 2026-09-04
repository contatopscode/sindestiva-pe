// =============================================================================
// SINDESTIVA-PE · /navios/novo — cadastro manual de navio (issue #15)
// =============================================================================

import Link from "next/link";
import type { ReactNode } from "react";

import { NavioForm } from "../_components/NavioForm";

export const metadata = { title: "Novo navio · SINDESTIVA-PE" };

export default function NovoNavioPage(): ReactNode {
  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Novo Navio</h1>
          <p className="section-subtitle">
            Cadastro manual do catálogo usado na lousa e no BI. Só o nome é obrigatório.
          </p>
        </div>
        <Link
          href="/navios"
          className="rounded border border-[#1e3a5f] px-4 py-2 text-[12px] font-bold text-[#8fa8c0] hover:text-[#e6edf3]"
        >
          ← Voltar
        </Link>
      </div>

      <NavioForm />
    </div>
  );
}
