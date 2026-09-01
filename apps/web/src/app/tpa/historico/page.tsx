// =============================================================================
// SINDESTIVA-PE · /tpa/historico — PWA TPA · Histórico
// =============================================================================

import type { ReactNode } from "react";
import { StatusBadge, toneForCellStatus } from "@/app/_components/StatusBadge";
import { getMockLousaPreview } from "@/lib/mock";

export const metadata = { title: "PWA · Histórico · SINDESTIVA-PE" };

const DIAS = ["Hoje", "Ontem", "Anteontem", "Há 3 dias", "Há 4 dias", "Há 5 dias", "Há 6 dias"];

export default function TpaHistoricoPage(): ReactNode {
  const lousa = getMockLousaPreview("SUAPE", "DIURNO");
  const tpa = { matricula: "247" };
  const cells = lousa.cells.filter((c) => c.tpa_matricula === tpa.matricula);
  const fainasById = new Map(lousa.fainas.map((f) => [f.id, f]));
  const funcoesById = new Map(lousa.funcoes.map((f) => [f.id, f]));

  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Histórico</h1>
          <p className="section-subtitle">Suas escalas dos últimos 7 dias (mock)</p>
        </div>
      </div>

      {cells.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#2a5070] bg-[#0f2438] p-8 text-center">
          <div className="text-base font-semibold text-[#e8eef4]">Sem escalas no histórico</div>
        </div>
      ) : (
        <ul className="space-y-2">
          {DIAS.map((dia, i) => {
            // Reaproveita os mesmos cells do mock, só varia o "dia".
            const c = cells[i % cells.length];
            if (!c) return null;
            const faina = fainasById.get(c.faina_id);
            const funcao = funcoesById.get(c.funcao_id);
            return (
              <li
                key={dia}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-[#1e3a52] bg-[#0f2438] p-3"
              >
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-[#94a8bd]">
                    {dia}
                  </div>
                  <div className="mt-1 text-[13px] font-semibold text-[#e8eef4]">
                    {faina?.nome ?? "—"} · {funcao?.nome ?? "—"} · Cais {c.cais ?? "—"}
                  </div>
                </div>
                <StatusBadge tone={toneForCellStatus(c.status)}>
                  {c.status === "NORMAL" ? "Presente" : c.status}
                </StatusBadge>
              </li>
            );
          })}
        </ul>
      )}

      <div className="mt-6 rounded-md border border-[#1e3a52] bg-[#0a1929] p-3 text-[11px] text-[#94a8bd]">
        Em produção, esta tela lê de <code className="font-mono">/api/v1/tpa/escalas?dias=7</code> (Sprint 3, T3-05).
      </div>
    </div>
  );
}
