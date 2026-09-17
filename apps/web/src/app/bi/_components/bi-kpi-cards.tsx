"use client";

import type { ReactNode } from "react";
import type { BIKpis, PeriodoDias } from "@/lib/tipos";
import {
  folhaPagaCardDetail,
  formatBrlCompact,
  formatCausaFaltaMotivo,
  formatPercentualInteiro,
  formatTaxaComparecimento,
} from "../bi-ui";

export function BiKpiCards({
  kpis,
  periodo,
}: {
  kpis: BIKpis;
  periodo: PeriodoDias;
}): ReactNode {
  const causaPct = formatPercentualInteiro(kpis.causa_principal_falta.percentual);
  const nackPct = formatPercentualInteiro(kpis.percentual_nack.percentual);

  return (
    <section
      className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      data-testid="bi-kpi-row"
    >
      <KpiCard
        label="Taxa Comparecimento"
        value={formatTaxaComparecimento(kpis.comparecimento.percentual)}
        detail={`${kpis.comparecimento.total_confirmados}/${kpis.comparecimento.total_escalados} TPAs confirmados`}
      />
      <KpiCard
        label="Folha paga"
        value={formatBrlCompact(kpis.folha_paga.valor_total_brl)}
        detail={folhaPagaCardDetail(periodo, kpis.comparecimento.total_escalados)}
        accentTop="green"
      />
      <KpiCard
        label="Causa #1 Falta"
        value={formatCausaFaltaMotivo(kpis.causa_principal_falta.motivo)}
        detail={`${causaPct} do total`}
      />
      <KpiCard
        label="Remanejamentos c/ OGMO NACK"
        value={nackPct}
        detail="Justificativa CCT"
        detailClassName="text-[#e04a4a]"
      />
    </section>
  );
}

function KpiCard({
  label,
  value,
  detail,
  detailClassName = "text-[#94a8bd]",
  accentTop,
}: {
  label: string;
  value: string;
  detail: string;
  detailClassName?: string;
  accentTop?: "green";
}): ReactNode {
  return (
    <div
      className={`rounded-lg border border-[#2a5070] bg-[#0f2438] p-4 ${
        accentTop === "green" ? "border-t-2 border-t-green-500" : ""
      }`}
    >
      <div className="text-[10px] font-semibold uppercase tracking-wider text-[#94a8bd]">
        {label}
      </div>
      <div className="mt-1 text-2xl font-bold text-[#e8eef4]">{value}</div>
      <div className={`mt-0.5 text-xs ${detailClassName}`}>{detail}</div>
    </div>
  );
}
