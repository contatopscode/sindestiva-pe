"use client";

import type { ReactNode } from "react";
import type { TopCard, TopCards } from "@/lib/tipos";
import { formatPercentualInteiro } from "../bi-ui";

export function BiTopCards({ cards }: { cards: TopCards }): ReactNode {
  return (
    <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3" data-testid="bi-top-cards">
      <MiniCard
        titulo="Função + remanejada"
        card={cards.funcao_mais_remanejada}
        valueClassName="text-[#c8a04d]"
        subtext={(c) => `${formatPercentualInteiro(c.percentual)} do total`}
      />
      <MiniCard
        titulo="Cais + problemático"
        card={cards.cais_mais_problematico}
        valueClassName="text-[#e04a4a]"
        subtext={(c) => `${c.total} remanejamentos · ${formatPercentualInteiro(c.percentual)}`}
      />
      <MiniCard
        titulo="Horário + crítico"
        card={cards.horario_mais_critico}
        valueClassName="text-cyan-400"
        subtext={(c) => `${formatPercentualInteiro(c.percentual)} do total`}
      />
    </div>
  );
}

function MiniCard({
  titulo,
  card,
  valueClassName,
  subtext,
}: {
  titulo: string;
  card: TopCard | null;
  valueClassName: string;
  subtext: (card: TopCard) => string;
}): ReactNode {
  return (
    <div className="rounded-lg border border-[#2a5070] bg-[#0a1828] p-3">
      <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[#94a8bd]">
        {titulo}
      </h3>
      {card ? (
        <>
          <p className={`mt-1 text-lg font-bold ${valueClassName}`}>{card.label}</p>
          <p className="text-xs text-[#94a8bd]">{subtext(card)}</p>
        </>
      ) : (
        <>
          <p className={`mt-1 text-lg font-bold text-[#94a8bd]`}>—</p>
          <p className="text-xs text-[#94a8bd]">0% do total</p>
        </>
      )}
    </div>
  );
}
