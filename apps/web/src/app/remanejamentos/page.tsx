// =============================================================================
// SINDESTIVA-PE · /remanejamentos — lista de remanejamentos (Sprint S2)
// Agora client component (busca via apiFetch + useEffect).
// Sprint S2: tipo do state migrou para `RemanejamentoItemResolved` (dados
// crus do backend + campos resolvidos via catálogo carregado em paralelo).
// =============================================================================

"use client";

import { useEffect, useState, type ReactNode } from "react";
import { getRemanejamentos, getLousaPreview, ApiError } from "@/lib/api";
import type { Porto } from "@sindestiva/shared";
import { EmptyState } from "@/app/_components/EmptyState";
import { RemanejamentosTable } from "./_components/RemanejamentosTable";
import type { RemanejamentoItemResolved } from "@/lib/api-mappers";

export default function RemanejamentosPage(): ReactNode {
  const [items, setItems] = useState<RemanejamentoItemResolved[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    // Carrega remanejamentos + catálogo (preview público) em paralelo (D01).
    Promise.all([
      getRemanejamentos(),
      getLousaPreview("SUAPE" as Porto, "DIURNO").catch(() => null),
    ])
      .then(([remanejamentos, preview]) => {
        if (cancelled) return;
        setItems(preview ? normalizeComCatalogo(remanejamentos, preview) : remanejamentos);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError ? err.detail : err instanceof Error ? err.message : "Erro";
        setError(msg);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // KPIs (réplica T5-09, ajustada para os 6 status do `StatusRemanejamentoUi`).
  const total = items.length;
  const pendentes = items.filter((r) => r.status === "PENDENTE").length;
  const aprovados = items.filter((r) => r.status === "APROVADO").length;
  const notificados = items.filter((r) => r.status === "NOTIFICADO_OGMO" || r.status === "ACK").length;
  const recusados = items.filter((r) => r.status === "NACK" || r.status === "CANCELADO").length;

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
              <div className="kpi-label">Prontos p/ OGMO</div>
              <div className="kpi-value">{aprovados}</div>
            </div>
            <div className="kpi-card green">
              <div className="kpi-label">Notificados</div>
              <div className="kpi-value">{notificados}</div>
            </div>
            <div className="kpi-card red">
              <div className="kpi-label">Recusados/Cancelados</div>
              <div className="kpi-value">{recusados}</div>
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

/**
 * Aplica o catálogo (cells/fainas/funções) aos itens crus do backend para
 * resolver nomes legíveis (TPA, matrícula, faina, função). É uma forma
 * simplificada de aplicar o mapper no client quando o `getRemanejamentos`
 * não recebeu catálogo (helper local — equivalente ao uso de
 * `mapRemanejamentoRead` direto).
 */
function normalizeComCatalogo(
  itens: RemanejamentoItemResolved[],
  preview: import("@/lib/tipos").LousaPreviewResponse,
): RemanejamentoItemResolved[] {
  return itens.map((item) => {
    const cellOut = preview.cells.find((c) => c.tpa_id === item.tpa_out_id) ?? null;
    const cellIn = item.tpa_in_id
      ? preview.cells.find((c) => c.tpa_id === item.tpa_in_id) ?? null
      : null;
    const funcao = preview.funcoes.find((f) => f.id === item.funcao_origem_id) ?? null;
    const faina = preview.fainas.find((f) => f.id === item.faina_origem_id) ?? null;
    return {
      ...item,
      tpa_removido_nome: cellOut?.tpa_nome ?? "(nome removido)",
      tpa_removido_matricula: cellOut?.tpa_matricula ?? "—",
      funcao_origem_nome: funcao?.nome ?? "(função removida)",
      funcao_origem_codigo: funcao?.codigo ?? "—",
      faina_origem_nome: faina?.nome ?? "(faina removida)",
      faina_origem_codigo: faina?.codigo ?? "—",
      ...(cellIn?.tpa_nome ? { tpa_substituto_nome: cellIn.tpa_nome } : {}),
    };
  });
}
