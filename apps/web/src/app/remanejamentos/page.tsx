// =============================================================================
// SINDESTIVA-PE · /remanejamentos — lista de remanejamentos (Sprint B)
// Agora client component (busca via apiFetch + useEffect).
// =============================================================================

"use client";

import { useEffect, useState, type ReactNode } from "react";
import { getRemanejamentos, ApiError } from "@/lib/api";
import type { RemanejamentoItem } from "@/lib/tipos";
import { EmptyState } from "@/app/_components/EmptyState";
import { RemanejamentosTable } from "./_components/RemanejamentosTable";

export default function RemanejamentosPage(): ReactNode {
  const [items, setItems] = useState<RemanejamentoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getRemanejamentos()
      .then((data) => {
        setItems(data);
        setLoading(false);
      })
      .catch((err) => {
        const msg =
          err instanceof ApiError ? err.detail : err instanceof Error ? err.message : "Erro";
        setError(msg);
        setLoading(false);
      });
  }, []);

  // KPIs (réplica T5-09) — usa a lista carregada do servidor.
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

      {loading && <div className="loading">Carregando remanejamentos…</div>}
      {error && (
        <div className="login-error" role="alert">
          ⚠ {error}
        </div>
      )}

      {!loading && !error && (
        <>
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

          {items.length === 0 ? (
            <EmptyState
              icon="📋"
              title="Nenhum remanejamento registrado"
              description="Quando o fiscal registrar remanejamentos no turno, eles aparecerão aqui com status de notificação ao OGMO."
            />
          ) : (
            <RemanejamentosTable items={items} />
          )}
        </>
      )}
    </div>
  );
}
