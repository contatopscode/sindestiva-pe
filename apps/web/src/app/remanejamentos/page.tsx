// =============================================================================
// SINDESTIVA-PE · /remanejamentos — lista de remanejamentos (Sprint S4)
//
// Mudanças vs S3:
//   - Catálogo entregue à `RemanejamentosTable` via prop `catalogo` —
//     a resolução de IDs via catálogo passa a ser responsabilidade da
//     tabela (memoizada) e não mais da página.
//   - KPIs calculados em `useMemo` com base nos status crus do enum
//     `StatusRemanejamentoUi` (PENDENTE / APROVADO /
//     NOTIFICADO_OGMO|ACK / NACK|CANCELADO).
//   - Botão "Notificar OGMO" (status APROVADO) + optimistic update + debounce
//     expostos pela tabela; a página só repassa `onNotify` e mantém o estado.
//   - Paginação client-side com `limit=50` (botões Anterior/Próximo).
// =============================================================================

"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  getRemanejamentos,
  getLousaPreview,
  notifyOgmo,
  ApiError,
} from "@/lib/api";
import type { Porto } from "@sindestiva/shared";
import { EmptyState } from "@/app/_components/EmptyState";
import { RemanejamentosTable } from "./_components/RemanejamentosTable";
import { useToast } from "@/lib/toast";
import type {
  LousaCellOut,
  LousaPreviewResponse,
} from "@/lib/tipos";
import type {
  RemanejamentoItemResolved,
} from "@/lib/api-mappers";

export default function RemanejamentosPage(): ReactNode {
  const [items, setItems] = useState<RemanejamentoItemResolved[]>([]);
  const [preview, setPreview] = useState<LousaPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Carrega remanejamentos + catálogo (preview público) em paralelo (D01).
      // O backend aplica defaults skip=0&limit=50; para esgotar o volume
      // esperado (~300 remanejamentos/mês segundo discovery-notes) e
      // preservar a paginação client-side + busca em todas as páginas,
      // solicitamos limit=500 (teto do backend — apps/api/app/api/v1/
      // remanejamentos.py:43). A tabela pagina client-side sobre o
      // total recebido. CR2 — correção do achado ALTO da revisão
      // (frontend violava `le=200`; backend foi elevado para `le=500`).
      const porto: Porto = "SUAPE";
      const [remanejamentos, previewData] = await Promise.all([
        getRemanejamentos({ skip: 0, limit: 500 }),
        getLousaPreview(porto, "DIURNO").catch(() => null),
      ]);
      setItems(remanejamentos);
      setPreview(previewData);
      setLoading(false);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Erro";
      setError(msg);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // KPIs calculados em useMemo a partir dos status crus (E7 da SPEC §5.6).
  const kpis = useMemo(() => {
    const pendentes = items.filter((r) => r.status === "PENDENTE").length;
    const aprovados = items.filter((r) => r.status === "APROVADO").length;
    const notificados = items.filter(
      (r) => r.status === "NOTIFICADO_OGMO" || r.status === "ACK",
    ).length;
    const recusados = items.filter(
      (r) => r.status === "NACK" || r.status === "CANCELADO",
    ).length;
    return {
      total: items.length,
      pendentes,
      aprovados,
      notificados,
      recusados,
    };
  }, [items]);

  /**
   * Ação "Notificar OGMO" (HU002/CA03) — disparada pela tabela.
   * Faz optimistic update local (status → NOTIFICADO_OGMO) e revalida a
   * lista em background. Em 409 INVALID_STATE mostra toast e mantém
   * estado pendente (D13). Em outros erros reverte e mostra toast.
   */
  const onNotify = useCallback(
    async (id: string) => {
      const anterior = items.find((r) => r.id === id)?.status ?? "PENDENTE";
      setItems((prev) =>
        prev.map((r) => (r.id === id ? { ...r, status: "NOTIFICADO_OGMO" } : r)),
      );
      try {
        await notifyOgmo(id);
        toast.showSuccess("Notificação enviada ao OGMO.");
        // Refresh em background — o backend pode ter persistido FALHOU
        // (RNF-12) e isso precisa refletir na UI.
        fetchAll();
      } catch (err) {
        // 409 INVALID_STATE: status mudou, mantém como PENDENTE (D13).
        if (err instanceof ApiError && err.status === 409) {
          setItems((prev) =>
            prev.map((r) => (r.id === id ? { ...r, status: "PENDENTE" } : r)),
          );
          toast.showError("Status mudou. Atualize a fila.");
          fetchAll();
          return;
        }
        // Outros erros: restaura status anterior.
        setItems((prev) =>
          prev.map((r) => (r.id === id ? { ...r, status: anterior } : r)),
        );
        const detail =
          err instanceof ApiError
            ? err.detail
            : err instanceof Error
              ? err.message
              : "Erro";
        toast.showError(`Falha ao notificar OGMO: ${detail}`);
      }
    },
    [items, toast, fetchAll],
  );

  // Catálogo derivado do preview (passado à tabela para resolução client-side).
  const catalogo = useMemo(() => {
    const cells: LousaCellOut[] = preview?.cells ?? [];
    const fainas = preview?.fainas ?? [];
    const funcoes = preview?.funcoes ?? [];
    return { cells, fainas, funcoes };
  }, [preview]);

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
              <div className="kpi-value">{kpis.total}</div>
            </div>
            <div className="kpi-card amber">
              <div className="kpi-label">Pendentes</div>
              <div className="kpi-value">{kpis.pendentes}</div>
            </div>
            <div className="kpi-card cyan">
              <div className="kpi-label">Prontos p/ OGMO</div>
              <div className="kpi-value">{kpis.aprovados}</div>
            </div>
            <div className="kpi-card green">
              <div className="kpi-label">Notificados</div>
              <div className="kpi-value">{kpis.notificados}</div>
            </div>
            <div className="kpi-card red">
              <div className="kpi-label">Recusados/Cancelados</div>
              <div className="kpi-value">{kpis.recusados}</div>
            </div>
          </div>

          {items.length === 0 ? (
            <EmptyState
              icon="📋"
              title="Nenhum remanejamento registrado"
              description="Quando o fiscal registrar remanejamentos no turno, eles aparecerão aqui com status de notificação ao OGMO."
            />
          ) : (
            <RemanejamentosTable
              items={items}
              catalogo={catalogo}
              onNotify={onNotify}
            />
          )}
        </>
      )}
    </div>
  );
}
