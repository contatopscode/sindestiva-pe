// =============================================================================
// SINDESTIVA-PE · OgmoNotificacoesList — fila de notificações OGMO/PE
// Sprint S4 — UX completa da HU005:
//   - 5 status distintos (PENDENTE/ENVIADO/ENTREGUE/FALHOU/REJEITADO) com
//     tons distintos via `toneForNotificacaoStatus`.
//   - KPIs do topo: Pendentes / Enviados (ENVIADO+ENTREGUE) / Falhas
//     (FALHOU+REJEITADO) / Total — clicáveis como atalho para o filtro.
//   - Coluna "Ação" com botão "Reenviar" para `status === 'FALHOU'` +
//     debounce 5s + tratamento de 409 INVALID_STATE e 5xx.
//   - Tooltip "Entregue ao OGMO em DD/MM HH:MM (provider: <id>)" em
//     ENTREGUE (E21) e "Anexo indisponível" quando `pdf_anexo_url`
//     é null em ENTREGUE/ENVIADO (E36).
//   - Ordenação default `enviado_at desc` (E19) e paginação
//     Anterior/Próximo com `limit=50` (E20).
// =============================================================================

"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  getOgmoNotificacoes,
  resendOgmoNotificacao,
  ApiError,
} from "@/lib/api";
import type { OgmoNotificacao, StatusNotificacaoUi } from "@/lib/tipos";
import { StatusBadge, toneForNotificacaoStatus } from "@/app/_components/StatusBadge";
import { EmptyState } from "@/app/_components/EmptyState";
import { useToast } from "@/lib/toast";

const STATUSES: Array<StatusNotificacaoUi | "TODOS"> = [
  "TODOS",
  "PENDENTE",
  "ENVIADO",
  "ENTREGUE",
  "FALHOU",
  "REJEITADO",
];

/** Limite de itens por página (E20). */
const PAGE_LIMIT = 50;
/** Debounce do botão "Reenviar" em ms (D22/E11). */
const RESEND_DEBOUNCE_MS = 5_000;

/** Formatador "DD/MM HH:MM" para tooltips E21. */
function formatarDataCurta(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** Tooltip em ENTREGUE: "Entregue ao OGMO em DD/MM HH:MM (provider: <id>)". */
function tooltipEntregue(item: OgmoNotificacao): string | undefined {
  if (item.status !== "ENTREGUE") return undefined;
  const dataFmt = formatarDataCurta(item.entregue_at);
  const provider = item.provider_message_id ?? "n/a";
  return `Entregue ao OGMO em ${dataFmt} (provider: ${provider})`;
}

/** Tooltip "Anexo indisponível" quando pdf_anexo_url === null em ENTREGUE/ENVIADO (E36). */
function tooltipAnexo(item: OgmoNotificacao): string | undefined {
  if (item.pdf_anexo_url !== null) return undefined;
  if (item.status === "ENTREGUE" || item.status === "ENVIADO") {
    return "Anexo indisponível";
  }
  return undefined;
}

/** Tooltip final: prioriza anexo indisponível (E36) > entrega E21. */
function tooltipFinal(item: OgmoNotificacao): string | undefined {
  const anexo = tooltipAnexo(item);
  if (anexo) return anexo;
  return tooltipEntregue(item);
}

export function OgmoNotificacoesList(): ReactNode {
  const [items, setItems] = useState<OgmoNotificacao[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<
    StatusNotificacaoUi | "TODOS"
  >("TODOS");
  const [skip, setSkip] = useState(0);
  /** IDs com ação "Reenviar" em curso — usado para desabilitar + debounce. */
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set());
  const busyTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const toast = useToast();

  // ---- Carregamento inicial -----------------------------------------------
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getOgmoNotificacoes();
      // Ordenação default: enviado_at desc (E19).
      data.sort((a, b) => {
        const av = Date.parse(a.data_hora);
        const bv = Date.parse(b.data_hora);
        return bv - av;
      });
      setItems(data);
      setLoading(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setItems([]);
        setLoading(false);
        return;
      }
      setError(
        e instanceof ApiError ? e.detail : String(e instanceof Error ? e.message : e),
      );
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Cleanup dos timers de debounce ao desmontar.
  useEffect(() => {
    const timers = busyTimers.current;
    return () => {
      for (const t of timers.values()) clearTimeout(t);
      timers.clear();
    };
  }, []);

  // ---- KPIs (memoizados) --------------------------------------------------
  const kpis = useMemo(() => {
    const pendentes = items.filter((i) => i.status === "PENDENTE").length;
    const enviados = items.filter(
      (i) => i.status === "ENVIADO" || i.status === "ENTREGUE",
    ).length;
    const falhas = items.filter(
      (i) => i.status === "FALHOU" || i.status === "REJEITADO",
    ).length;
    return { pendentes, enviados, falhas, total: items.length };
  }, [items]);

  // ---- Filtro + paginação -------------------------------------------------
  const filtered = useMemo(() => {
    if (statusFilter === "TODOS") return items;
    return items.filter((i) => i.status === statusFilter);
  }, [items, statusFilter]);

  const total = filtered.length;
  const pageStart = skip;
  const pageEnd = Math.min(skip + PAGE_LIMIT, total);
  const pageItems = useMemo(
    () => filtered.slice(pageStart, pageEnd),
    [filtered, pageStart, pageEnd],
  );

  // ---- Ação "Reenviar" (HU005) --------------------------------------------
  const handleResend = useCallback(
    async (remanejamentoId: string, currentId: string) => {
      if (busyIds.has(currentId)) return;
      setBusyIds((prev) => {
        const next = new Set(prev);
        next.add(currentId);
        return next;
      });
      try {
        await resendOgmoNotificacao(remanejamentoId);
        toast.showSuccess("Notificação reenviada ao OGMO.");
        fetchData();
      } catch (err) {
        // 409 INVALID_STATE: mantém linha como PENDENTE (D13).
        if (err instanceof ApiError && err.status === 409) {
          setItems((prev) =>
            prev.map((it) =>
              it.id === currentId ? { ...it, status: "PENDENTE" } : it,
            ),
          );
          toast.showError("Status mudou. Atualize a fila.");
          fetchData();
          return;
        }
        // 5xx: mantém linha como FALHOU (E22 — backend persiste via
        // _persist_failure; UI só dá feedback sem mudar o estado).
        if (err instanceof ApiError && err.status >= 500) {
          toast.showError("Falha ao reenviar. Tente novamente em instantes.");
          // linha permanece FALHOU — nada a fazer
          return;
        }
        // Outros erros: mostra mensagem genérica.
        const detail =
          err instanceof ApiError
            ? err.detail
            : err instanceof Error
              ? err.message
              : "Erro";
        toast.showError(`Falha ao reenviar: ${detail}`);
      } finally {
        // Debounce 5s (D22/E11): mantém busy durante esse intervalo
        // mesmo se a mutate resolver instantaneamente.
        const timer = setTimeout(() => {
          setBusyIds((prev) => {
            const next = new Set(prev);
            next.delete(currentId);
            return next;
          });
          busyTimers.current.delete(currentId);
        }, RESEND_DEBOUNCE_MS);
        busyTimers.current.set(currentId, timer);
      }
    },
    [busyIds, fetchData, toast],
  );

  // ---- Estados de carregamento --------------------------------------------
  if (loading && items.length === 0) {
    return <div className="loading">Carregando fila OGMO…</div>;
  }
  if (error && items.length === 0) {
    return (
      <div className="error-box">
        ❌ Erro ao carregar fila OGMO: <strong>{error}</strong>
      </div>
    );
  }

  // ---- KPIs clicáveis como atalho para o filtro (E23) --------------------
  function setFilterFromKpi(kpi: "PENDENTE" | "ENVIADO" | "FALHOU" | "TODOS") {
    if (kpi === "TODOS") {
      setStatusFilter("TODOS");
      setSkip(0);
      return;
    }
    // KPI "Enviados" cobre ENVIADO + ENTREGUE → escolhe ENVIADO.
    // KPI "Falhas" cobre FALHOU + REJEITADO → escolhe FALHOU.
    setStatusFilter(kpi);
    setSkip(0);
  }

  return (
    <div className="space-y-4">
      <div className="kpi-row">
        <button
          type="button"
          onClick={() => setFilterFromKpi("PENDENTE")}
          className="kpi-card amber cursor-pointer text-left transition hover:border-[#e8a33d]"
        >
          <div className="kpi-label">Pendentes</div>
          <div className="kpi-value">{kpis.pendentes}</div>
        </button>
        <button
          type="button"
          onClick={() => setFilterFromKpi("ENVIADO")}
          className="kpi-card cyan cursor-pointer text-left transition hover:border-[#4fb8c9]"
        >
          <div className="kpi-label">Enviados</div>
          <div className="kpi-value">{kpis.enviados}</div>
        </button>
        <button
          type="button"
          onClick={() => setFilterFromKpi("FALHOU")}
          className="kpi-card red cursor-pointer text-left transition hover:border-[#e04a4a]"
        >
          <div className="kpi-label">Falhas</div>
          <div className="kpi-value">{kpis.falhas}</div>
        </button>
        <button
          type="button"
          onClick={() => setFilterFromKpi("TODOS")}
          className="kpi-card cursor-pointer text-left transition hover:border-[#d4a574]"
        >
          <div className="kpi-label">Total</div>
          <div className="kpi-value">{kpis.total}</div>
        </button>
      </div>

      <div className="rounded-lg border border-[#1e3a52] bg-[#0f2438]">
        {/* Toolbar de filtro */}
        <div className="flex flex-wrap items-center gap-2 border-b border-[#1e3a52] p-3">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as StatusNotificacaoUi | "TODOS");
              setSkip(0);
            }}
            className="rounded border border-[#2a5070] bg-[#0a1929] px-2 py-2 text-[12px] text-[#e8eef4]"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <span className="ml-auto text-[10px] text-[#94a8bd]">
            {items.length} notificações · status exibidos:{" "}
            {STATUSES.filter((s) => s !== "TODOS").join(" · ")}
          </span>
        </div>

        {/* Tabela */}
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
                <th className="px-3 py-2">Ação</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-[#94a8bd]">
                    <EmptyState
                      title="Fila OGMO vazia"
                      description="Nenhuma notificação registrada ainda."
                    />
                  </td>
                </tr>
              ) : pageItems.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-[#94a8bd]">
                    Nenhuma notificação com status {statusFilter}.
                  </td>
                </tr>
              ) : (
                pageItems.map((i) => {
                  const tooltip = tooltipFinal(i);
                  const busy = busyIds.has(i.id);
                  const canResend = i.status === "FALHOU";
                  return (
                    <tr
                      key={i.id}
                      className="border-b border-[#1e3a52] hover:bg-[#163554]/40"
                    >
                      <td className="px-3 py-2 font-mono text-[#d4a574]">
                        {new Date(i.data_hora).toLocaleString("pt-BR")}
                      </td>
                      <td className="px-3 py-2 font-mono text-[#e8eef4]">
                        {i.remanejamento_id.slice(0, 8)}…
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
                      <td className="px-3 py-2">
                        {canResend ? (
                          <button
                            type="button"
                            aria-label={`Reenviar notificação ${i.id}`}
                            disabled={busy}
                            onClick={() => handleResend(i.remanejamento_id, i.id)}
                            className="rounded bg-[#d4a574] px-3 py-1 text-[11px] font-bold text-[#0a1929] hover:bg-[#e8c49a] disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {busy ? "Enviando…" : "Reenviar"}
                          </button>
                        ) : (
                          <span className="text-[11px] text-[#5f7a92]">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Paginação */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#1e3a52] p-2 text-[10px] text-[#94a8bd]">
          <div className="font-mono">
            {total > 0
              ? `Mostrando ${pageStart + 1}–${pageEnd} de ${total}`
              : "Mostrando 0 de 0"}
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setSkip((s) => Math.max(0, s - PAGE_LIMIT))}
              disabled={skip === 0}
              className="rounded border border-[#2a5070] bg-[#0a1929] px-2 py-1 text-[11px] font-bold text-[#e8eef4] hover:border-[#d4a574] disabled:cursor-not-allowed disabled:opacity-50"
            >
              ← Anterior
            </button>
            <button
              type="button"
              onClick={() =>
                setSkip((s) => (s + PAGE_LIMIT < total ? s + PAGE_LIMIT : s))
              }
              disabled={skip + PAGE_LIMIT >= total}
              className="rounded border border-[#2a5070] bg-[#0a1929] px-2 py-1 text-[11px] font-bold text-[#e8eef4] hover:border-[#d4a574] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Próximo →
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-md border border-[#9b7ec4]/40 bg-[#9b7ec4]/10 p-3 text-[11px] text-[#9b7ec4]">
        💡 Status exibidos: {STATUSES.filter((s) => s !== "TODOS").join(" · ")}.
        O webhook HMAC-SHA256 (Sprint 5 T5-07) está preparado mas inativo: o
        OGMO/PE ainda não topou expor endpoint (Risco R1 do plano v1.0).
        Mitigação ativa: notificação por e-mail funciona unilateralmente.
      </div>
    </div>
  );
}
