"use client";

import type { ReactNode } from "react";
import type { Insight, PeriodoDias, TopRemanejados } from "@/lib/tipos";
import { topRemanejadosPeriodBadge } from "../bi-ui";

export function BiTopRemanejadosColumn({
  top,
  periodo,
  primaryInsight,
}: {
  top: TopRemanejados;
  periodo: PeriodoDias;
  primaryInsight: Insight | null;
}): ReactNode {
  return (
    <div
      className="flex h-full flex-col rounded-lg border border-[#2a5070] bg-[#0f2438] p-4"
      data-testid="bi-top-remanejados"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[#e8eef4]">
          🏆 TOP REMANEJADOS
        </h2>
        <span className="rounded bg-[#1a2540] px-2 py-0.5 text-[10px] font-semibold text-[#94a8bd]">
          {topRemanejadosPeriodBadge(periodo)}
        </span>
      </div>

      {top.items.length > 0 ? (
        <ol className="flex-1 space-y-2">
          {top.items.map((t, idx) => (
            <li
              key={t.tpa_id}
              className="flex items-center justify-between border-b border-[#1a2540] pb-1.5 text-sm"
            >
              <span className="text-[#e8eef4]">
                <span className="text-[#94a8bd]">{idx + 1}º</span> {t.tpa_nome}
              </span>
              <span className="font-mono text-sm font-semibold text-[#c8a04d]">
                {t.total_remanejamentos}x
              </span>
            </li>
          ))}
        </ol>
      ) : (
        <ul className="flex-1 space-y-2 text-sm text-[#94a8bd]" aria-label="Lista vazia">
          {Array.from({ length: 5 }).map((_, idx) => (
            <li
              key={idx}
              className="flex items-center justify-between border-b border-[#1a2540] pb-1.5 opacity-40"
            >
              <span>{idx + 1}º —</span>
              <span>0x</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 rounded-lg border border-[#2a5070] bg-[#0a1828] p-3 text-xs leading-relaxed text-[#94a8bd]">
        <span className="text-base" aria-hidden>💡</span>{" "}
        {primaryInsight ? (
          <>
            <strong className="text-[#e8eef4]">Insight:</strong> {primaryInsight.mensagem}
          </>
        ) : (
          <>
            <strong className="text-[#e8eef4]">Insight:</strong> Sem insights automáticos para o
            período selecionado. Os dados aparecem quando houver remanejamentos suficientes.
          </>
        )}
      </div>
    </div>
  );
}
