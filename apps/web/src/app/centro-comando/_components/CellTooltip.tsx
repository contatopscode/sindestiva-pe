// =============================================================================
// SINDESTIVA-PE · CellTooltip — popover com detalhes completos do TPA
// Acionado por hover (mouse) e focus (teclado) em cada ponteiro da lousa.
// =============================================================================

"use client";

import type { ReactNode } from "react";
import type { LousaCellOut, Funcao, Faina } from "@/lib/tipos";
import { CELL_STATUS_LABEL } from "@/lib/tipos";
import { toneForCellStatus, StatusBadge } from "@/app/_components/StatusBadge";

export interface CellTooltipProps {
  cell: LousaCellOut;
  funcao?: Funcao;
  faina?: Faina;
  /** Quando true, mostra o "Ver detalhes" (futuro modal). */
  showDetailsHint?: boolean;
}

/** CPF parcial: 123.***.***-45 (mock — não usar com dado real). */
function cpfParcial(seed: string | null | undefined): string {
  if (!seed) return "—";
  const n = (seed.charCodeAt(0) * 7 + seed.charCodeAt(seed.length - 1) * 11) % 1000;
  return `${(n + 100).toString().slice(-3)}.***.***-**`;
}

export function CellTooltip({ cell, funcao, faina, showDetailsHint = true }: CellTooltipProps): ReactNode {
  const isEmpty = !cell.tpa_id;
  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-50 w-64 rounded-md border border-[#2a5070] bg-[#0a1929] p-3 text-left text-[12px] text-[#e8eef4] shadow-lg"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="font-mono text-[11px] text-[#d4a574]">
          {cell.tpa_matricula ?? "VAZIO"}
        </div>
        <StatusBadge tone={toneForCellStatus(cell.status)}>
          {CELL_STATUS_LABEL[cell.status]}
        </StatusBadge>
      </div>

      {isEmpty ? (
        <div className="text-[#5f7a92]">
          Célula sem TPA escalado para {funcao?.nome ?? "—"} em {faina?.nome ?? "—"}.
        </div>
      ) : (
        <>
          <div className="mb-2 font-semibold leading-tight">{cell.tpa_nome ?? "(sem nome)"}</div>
          <dl className="grid grid-cols-[80px_1fr] gap-y-1 text-[11px]">
            <dt className="text-[#94a8bd]">CPF</dt>
            <dd className="font-mono text-[#e8eef4]">{cpfParcial(cell.tpa_matricula)}</dd>
            <dt className="text-[#94a8bd]">Função</dt>
            <dd>{funcao?.nome ?? "—"}</dd>
            <dt className="text-[#94a8bd]">Faina</dt>
            <dd>{faina?.nome ?? "—"}</dd>
            <dt className="text-[#94a8bd]">Cais</dt>
            <dd className="font-mono">{cell.cais ?? "—"}</dd>
            <dt className="text-[#94a8bd]">Data</dt>
            <dd className="font-mono">{cell.data_referencia}</dd>
          </dl>
        </>
      )}

      {showDetailsHint && !isEmpty && (
        <div className="mt-2 border-t border-[#1e3a52] pt-2 text-[10px] text-[#94a8bd]">
          Clique para abrir modal de remanejamento.
        </div>
      )}
    </div>
  );
}
