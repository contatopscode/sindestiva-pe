// =============================================================================
// SINDESTIVA-PE · /remanejamentos — lista de remanejamentos
// Sprint 0/4 mock; Sprint 5 (T5-09) implementa filtros + paginação real.
// =============================================================================

import type { ReactNode } from "react";
import { getRemanejamentos } from "@/lib/api";
import { RemanejamentosTable } from "./_components/RemanejamentosTable";

export const metadata = {
  title: "Remanejamentos · SINDESTIVA-PE",
};

export default async function RemanejamentosPage(): Promise<ReactNode> {
  const items = await getRemanejamentos();

  // KPIs (réplica T5-09)
  const total = items.length;
  const pendentes = items.filter((r) => r.status === "PEND").length;
  const enviados = items.filter((r) => r.status === "SENT").length;
  const ack = items.filter((r) => r.status === "ACK").length;

  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Remanejamentos</h1>
          <p className="section-subtitle">
            Histórico do turno · {new Date().toLocaleDateString("pt-BR")} · DIURNO
          </p>
        </div>
      </div>

      <div className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-label">Total</div>
          <div className="kpi-value">{total}</div>
        </div>
        <div className="kpi-card amber">
          <div className="kpi-label">Pendentes</div>
          <div className="kpi-value">{pendentes}</div>
        </div>
        <div className="kpi-card cyan">
          <div className="kpi-label">Enviados (SENT)</div>
          <div className="kpi-value">{enviados}</div>
        </div>
        <div className="kpi-card green">
          <div className="kpi-label">Confirmados (ACK)</div>
          <div className="kpi-value">{ack}</div>
        </div>
      </div>

      <RemanejamentosTable items={items} />
    </div>
  );
}
