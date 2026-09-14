// =============================================================================
// SINDESTIVA-PE · Histórico do turno (lista estilo protótipo)
// =============================================================================

"use client";

import { useMemo, type ReactNode } from "react";
import { shortHashPrefix } from "@/lib/api-mappers";
import type { RemanejamentoItemResolved } from "@/lib/api-mappers";
import {
  badgeLabelForRemanejamentoStatus,
  borderClassForRemanejamentoItem,
  cssClassForRemanejamentoBadge,
  formatMotivoLinha,
  isReferenciaHoje,
} from "@/lib/remanejamento-ui";

export interface RemanejamentosTableProps {
  items: RemanejamentoItemResolved[];
  /** ISO YYYY-MM-DD do turno exibido no subtítulo. */
  hojeIso: string;
}

function formatHora(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export function RemanejamentosTable({
  items,
  hojeIso,
}: RemanejamentosTableProps): ReactNode {
  const turnoItems = useMemo(
    () =>
      items
        .filter((r) => isReferenciaHoje(r.data_referencia, r.created_at, hojeIso))
        .sort(
          (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
        ),
    [items, hojeIso],
  );

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">Histórico do turno</div>
        <span className="tag gold">
          {turnoItems.length} evento{turnoItems.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="panel-body">
        {turnoItems.length === 0 ? (
          <p className="px-2 py-6 text-center text-[12px] text-[#94a8bd]">
            Nenhum remanejamento registrado para o turno de hoje.
          </p>
        ) : (
          turnoItems.map((r) => {
            const badge = badgeLabelForRemanejamentoStatus(r.status);
            const fiscal =
              r.fiscal_nome?.trim() ||
              `fiscal ${r.fiscal_id.slice(0, 8)}…`;
            const cais = r.cais_origem?.trim() || "—";
            const motivoLinha = formatMotivoLinha(
              r.motivo,
              r.motivo_outro_texto,
            );
            const nomeLinha = `${r.tpa_removido_nome} · ${r.tpa_removido_matricula} · ${r.funcao_origem_nome}`;
            return (
              <div
                key={r.id}
                className={`remanejamento-item bg-[#0f2438] ${borderClassForRemanejamentoItem(r.status)}`}
              >
                <div className="remanejamento-time">{formatHora(r.created_at)}</div>
                <div className="remanejamento-info">
                  <div className="name">{nomeLinha}</div>
                  <div className="meta">
                    Por {fiscal} · {cais} · {motivoLinha}
                  </div>
                  <div className="reason">
                    Hash: {shortHashPrefix(r.hash_evento, 12)}
                  </div>
                </div>
                <div
                  className={`remanejamento-status ${cssClassForRemanejamentoBadge(badge)}`}
                >
                  {badge}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
