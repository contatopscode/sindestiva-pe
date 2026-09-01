// =============================================================================
// SINDESTIVA-PE · /remanejamentos/novo
// Página dedicada de criação (além do modal pré-preenchido da lousa).
// Aceita query params: tpa, faina, funcao.
// =============================================================================

"use client";

import { Suspense, useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { RemanejamentoModal } from "../_components/RemanejamentoModal";
import type { Porto, Turno } from "@sindestiva/shared";
import { getCurrentUser } from "@/lib/api";

function NovoRemanejamentoContent(): ReactNode {
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(true);
  const [porto] = useState<Porto>("SUAPE");
  const [turno] = useState<Turno>("DIURNO");

  const prefill = {
    tpa_id: searchParams.get("tpa") ?? undefined,
    faina_codigo: searchParams.get("faina") ?? undefined,
    funcao_codigo: searchParams.get("funcao") ?? undefined,
  };

  const user = getCurrentUser();

  if (!open) {
    return (
      <div className="p-6">
        <div className="section-header">
          <div>
            <h1 className="section-title">Novo Remanejamento</h1>
            <p className="section-subtitle">Modal fechado.</p>
          </div>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a]"
          >
            Abrir formulário
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Novo Remanejamento</h1>
          <p className="section-subtitle">
            Operador: <span className="font-mono text-[#d4a574]">{user.nome}</span>
          </p>
        </div>
      </div>

      <RemanejamentoModal
        prefill={prefill}
        onCreated={() => {
          // poderia redirecionar pra /remanejamentos em produção
        }}
        onClose={() => setOpen(false)}
        porto={porto}
        turno={turno}
      />
    </div>
  );
}

export default function NovoRemanejamentoPage(): ReactNode {
  return (
    <Suspense fallback={<div className="loading">Carregando…</div>}>
      <NovoRemanejamentoContent />
    </Suspense>
  );
}
