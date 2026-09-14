// =============================================================================
// SINDESTIVA-PE · OgmoNotificacoesList — fila de notificações enviadas ao OGMO
// Sprint S2: 5 status de `StatusNotificacaoUi`
// (PENDENTE/ENVIADO/ENTREGUE/FALHOU/REJEITADO). UI completa da HU005
// (filtro dropdown, coluna Reenviar, debounce, tooltip de entrega) entra
// em sprint futura — aqui só ajustamos o tipo e os KPIs para os 5 valores.
// =============================================================================

"use client";

import { useEffect, useState, type ReactNode } from "react";
import { getOgmoNotificacoes, ApiError } from "@/lib/api";
import type { OgmoNotificacao, StatusNotificacaoUi } from "@/lib/tipos";
import { StatusBadge, toneForNotificacaoStatus } from "@/app/_components/StatusBadge";
import { EmptyState } from "@/app/_components/EmptyState";

const STATUSES: StatusNotificacaoUi[] = [
  "PENDENTE",
  "ENVIADO",
  "ENTREGUE",
  "FALHOU",
  "REJEITADO",
];

function formatTooltipEntregue(item: OgmoNotificacao): string | undefined {
  if (item.status !== "ENTREGUE" || !item.entregue_at) return undefined;
  const data = new Date(item.entregue_at);
  const dataFmt = `${String(data.getDate()).padStart(2, "0")}/${String(data.getMonth() + 1).padStart(2, "0")} ${String(data.getHours()).padStart(2, "0")}:${String(data.getMinutes()).padStart(2, "0")}`;
  const provider = item.provider_message_id ?? "n/a";
  return `Entregue ao OGMO em ${dataFmt} (provider: ${provider})`;
}

export function OgmoNotificacoesList(): ReactNode {
  const [items, setItems] = useState<OgmoNotificacao[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getOgmoNotificacoes()
      .then((d) => { if (!cancelled) setItems(d); })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) {
          setItems([]);
          return;
        }
        setError(e instanceof ApiError ? e.detail : String(e instanceof Error ? e.message : e));
      });
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return (
      <div className="error-box">
        ❌ Erro ao carregar fila OGMO: <strong>{error}</strong>
      </div>
    );
  }
  if (items === null) {
    return <div className="loading">Carregando fila OGMO…</div>;
  }
  if (items.length === 0) {
    return <EmptyState title="Fila OGMO vazia" description="Nenhuma notificação pendente." />;
  }

  const pendentes = items.filter((i) => i.status === "PENDENTE").length;
  const enviados = items.filter((i) => i.status === "ENVIADO" || i.status === "ENTREGUE").length;
  const falhas = items.filter((i) => i.status === "FALHOU" || i.status === "REJEITADO").length;

  return (
    <div className="space-y-4">
      <div className="kpi-row">
        <div className="kpi-card amber">
          <div className="kpi-label">Pendentes</div>
          <div className="kpi-value">{pendentes}</div>
        </div>
        <div className="kpi-card cyan">
          <div className="kpi-label">Enviados</div>
          <div className="kpi-value">{enviados}</div>
        </div>
        <div className="kpi-card red">
          <div className="kpi-label">Falhas</div>
          <div className="kpi-value">{falhas}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Total</div>
          <div className="kpi-value">{items.length}</div>
        </div>
      </div>

      <div className="rounded-lg border border-[#1e3a52] bg-[#0f2438]">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-[#1e3a52] bg-[#0a1929] text-left text-[10px] font-bold uppercase tracking-wider text-[#94a8bd]">
                <th className="px-3 py-2">Data/Hora</th>
                <th className="px-3 py-2">Remanejamento</th>
                <th className="px-3 py-2">Canal</th>
                <th className="px-3 py-2">Destinatário</th>
                <th className="px-3 py-2">Tentativas</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Último erro</th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => {
                const tooltip = formatTooltipEntregue(i);
                return (
                  <tr key={i.id} className="border-b border-[#1e3a52] hover:bg-[#163554]/40">
                    <td className="px-3 py-2 font-mono text-[#d4a574]">
                      {new Date(i.data_hora).toLocaleString("pt-BR")}
                    </td>
                    <td className="px-3 py-2 font-mono text-[#e8eef4]">
                      {i.remanejamento_id}
                    </td>
                    <td className="px-3 py-2">
                      <span className="rounded bg-[#1e3a52] px-2 py-0.5 text-[10px] font-bold uppercase text-[#94a8bd]">
                        {i.canal}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-[11px] text-[#94a8bd]">
                      {i.destinatario}
                    </td>
                    <td className="px-3 py-2 text-center font-mono text-[#e8eef4]">
                      {i.tentativas}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge tone={toneForNotificacaoStatus(i.status)} title={tooltip}>
                        {i.status}
                      </StatusBadge>
                    </td>
                    <td className="px-3 py-2 text-[11px] text-[#e04a4a]">
                      {i.ultimo_erro ?? <span className="text-[#5f7a92]">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-md border border-[#9b7ec4]/40 bg-[#9b7ec4]/10 p-3 text-[11px] text-[#9b7ec4]">
        💡 Status exibidos: {STATUSES.join(" · ")}. O webhook HMAC-SHA256 (Sprint 5 T5-07)
        está preparado mas inativo: o OGMO/PE ainda não topou expor endpoint
        (Risco R1 do plano v1.0). Mitigação ativa: notificação por e-mail
        funciona unilateralmente.
      </div>
    </div>
  );
}
