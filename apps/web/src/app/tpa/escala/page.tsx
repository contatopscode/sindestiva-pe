// =============================================================================
// SINDESTIVA-PE · /tpa/escala — PWA TPA · Escala do Dia
// Mock até Sprint 3 (apps/pwa/) implementar.
// =============================================================================

import type { ReactNode } from "react";
import { StatusBadge, toneForCellStatus } from "@/app/_components/StatusBadge";
import { getMockLousaPreview } from "@/lib/mock";
import type { Porto, Turno } from "@sindestiva/shared";

export const metadata = { title: "PWA · Escala do Dia · SINDESTIVA-PE" };

// Em produção: buscar do backend autenticado como TPA (CPF + matrícula OGMO).
function tpaMock(): { nome: string; matricula: string } {
  return { nome: "Manoel Costa (TPA)", matricula: "247" };
}

export default function TpaEscalaPage(): ReactNode {
  const porto: Porto = "SUAPE";
  const turno: Turno = "DIURNO";
  const lousa = getMockLousaPreview(porto, turno);
  const tpa = tpaMock();

  // Encontra cells em que o TPA logado está escalado.
  const minhas = lousa.cells.filter((c) => c.tpa_matricula === tpa.matricula);
  const fainasById = new Map(lousa.fainas.map((f) => [f.id, f]));
  const funcoesById = new Map(lousa.funcoes.map((f) => [f.id, f]));

  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Olá, {tpa.nome.split(" ")[0]} 👋</h1>
          <p className="section-subtitle">
            Sua escala de hoje · {lousa.turno.nome} · {porto}
          </p>
        </div>
      </div>

      {minhas.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#2a5070] bg-[#0f2438] p-8 text-center">
          <div className="mb-2 text-3xl">😴</div>
          <div className="text-base font-semibold text-[#e8eef4]">Você não está escalado hoje</div>
          <p className="mt-1 text-[12px] text-[#94a8bd]">
            Confira novamente mais tarde ou fale com o Fiscal.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {minhas.map((c) => {
            const faina = fainasById.get(c.faina_id);
            const funcao = funcoesById.get(c.funcao_id);
            return (
              <div
                key={c.id}
                className="rounded-lg border border-[#1e3a52] bg-[#0f2438] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-[#94a8bd]">
                      {faina?.nome ?? "—"} · {funcao?.nome ?? "—"}
                    </div>
                    <div className="mt-1 text-lg font-bold text-[#e8eef4]">
                      Cais {c.cais ?? "—"}
                    </div>
                    <div className="mt-1 text-[12px] text-[#94a8bd]">
                      Data: <span className="font-mono">{c.data_referencia}</span>
                    </div>
                  </div>
                  <StatusBadge tone={toneForCellStatus(c.status)} size="md">
                    {c.status === "NORMAL" ? "Presente" : c.status === "CONFIRMADO" ? "Confirmado" : c.status}
                  </StatusBadge>
                </div>

                {c.status === "NORMAL" && (
                  <button
                    type="button"
                    className="mt-3 w-full rounded bg-[#5dbb7d] px-4 py-2 text-[13px] font-bold text-[#061321] hover:bg-[#7dcd96]"
                  >
                    ✓ Confirmar Presença
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-6 rounded-md border border-[#1e3a52] bg-[#0a1929] p-3 text-[11px] text-[#94a8bd]">
        ℹ️ Em produção, esta tela é servida como PWA instalável em <code className="font-mono">apps/pwa/</code>
        (Sprint 3, T3-01 a T3-08). Aqui (Centro de Comando) é só uma visualização.
      </div>
    </div>
  );
}
