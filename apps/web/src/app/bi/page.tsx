// =============================================================================
// SINDESTIVA-PE · /bi — BI & Relatórios (layout protótipo CCT · dados reais API)
// Restrição: apenas DIRIGENTE (403 ROLE_REQUIRED).
// =============================================================================

"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  downloadBIPDF,
  getBIInsights,
  getBIKpis,
  getBIRemanejamentosPorDia,
  getBITopCards,
  getBITopRemanejados,
  getBIDrillDown,
  ApiError,
} from "@/lib/api";
import type {
  BIKpis,
  DrillDown,
  Insights,
  PeriodoDias,
  RemanejamentosPorDia,
  TopCards,
  TopRemanejados,
} from "@/lib/tipos";
import { BarChart } from "./_components/BarChart";
import { EmptyState } from "@/app/_components/EmptyState";
import { BiPeriodSelector } from "./_components/bi-period-selector";
import { BiKpiCards } from "./_components/bi-kpi-cards";
import { BiTopCards } from "./_components/bi-top-cards";
import { BiTopRemanejadosColumn } from "./_components/bi-top-remanejados";
import { formatRelativeSince, remanejamentosChartHeading } from "./bi-ui";

const AUTO_REFRESH_MS = 5 * 60 * 1000;

function extractDetailCode(detail: string): { code?: string; message: string } {
  const trimmed = detail.trim();
  if (trimmed.startsWith("{")) {
    try {
      const obj = JSON.parse(trimmed) as { code?: unknown; message?: unknown };
      if (typeof obj.code === "string" && typeof obj.message === "string") {
        return { code: obj.code, message: obj.message };
      }
    } catch {
      /* fallback */
    }
  }
  return { message: detail };
}

export default function BIPage(): ReactNode {
  const router = useRouter();

  const [periodo, setPeriodo] = useState<PeriodoDias>(7);
  const [kpis, setKpis] = useState<BIKpis | null>(null);
  const [porDia, setPorDia] = useState<RemanejamentosPorDia | null>(null);
  const [top, setTop] = useState<TopRemanejados | null>(null);
  const [cards, setCards] = useState<TopCards | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [drillDown, setDrillDown] = useState<DrillDown | null>(null);
  const [drillDownDate, setDrillDownDate] = useState<string | null>(null);
  const [drillDownError, setDrillDownError] = useState(false);
  const [drillDownLoading, setDrillDownLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState<{ code: string; message: string } | null>(
    null,
  );
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<Date | null>(null);
  const [relativeTick, setRelativeTick] = useState(0);

  const loadAll = useCallback(async (p: PeriodoDias): Promise<void> => {
    setLoading(true);
    setErro(null);
    setForbidden(null);
    try {
      const [k, d, t, c, i] = await Promise.all([
        getBIKpis(p),
        getBIRemanejamentosPorDia(p),
        getBITopRemanejados(p, 7),
        getBITopCards(p),
        getBIInsights(p),
      ]);
      setKpis(k);
      setPorDia(d);
      setTop(t);
      setCards(c);
      setInsights(i);
      setUltimaAtualizacao(new Date());
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        const { code, message } = extractDetailCode(e.detail);
        if (code === "ROLE_REQUIRED") {
          setForbidden({ code, message });
          setLoading(false);
          return;
        }
      }
      const msg =
        e instanceof ApiError
          ? `[${e.status}] ${e.detail}`
          : e instanceof Error
            ? e.message
            : "Erro ao carregar BI.";
      setErro(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll(periodo);
  }, [periodo, loadAll]);

  const periodoRef = useRef(periodo);
  useEffect(() => {
    periodoRef.current = periodo;
  }, [periodo]);

  useEffect(() => {
    const handle = setInterval(() => {
      void loadAll(periodoRef.current);
    }, AUTO_REFRESH_MS);
    return () => clearInterval(handle);
  }, [loadAll]);

  useEffect(() => {
    const tick = setInterval(() => setRelativeTick((n) => n + 1), 15_000);
    return () => clearInterval(tick);
  }, []);

  const handleBarClick = useCallback(async (item: { data: string }): Promise<void> => {
    setDrillDownDate(item.data);
    setDrillDown(null);
    setDrillDownError(false);
    setDrillDownLoading(true);
    try {
      const d = await getBIDrillDown(item.data);
      setDrillDown(d);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setDrillDownError(true);
      } else {
        setErro(e instanceof Error ? e.message : "Erro no drill-down.");
      }
    } finally {
      setDrillDownLoading(false);
    }
  }, []);

  const handleDownloadPdf = useCallback(async (): Promise<void> => {
    setDownloadingPdf(true);
    try {
      await downloadBIPDF(periodo);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao baixar PDF.");
    } finally {
      setDownloadingPdf(false);
    }
  }, [periodo]);

  const fecharDrillDown = useCallback((): void => {
    setDrillDown(null);
    setDrillDownDate(null);
    setDrillDownError(false);
  }, []);

  const primaryInsight = insights?.items[0] ?? null;
  const subtitleRelative =
    ultimaAtualizacao != null
      ? formatRelativeSince(ultimaAtualizacao)
      : loading
        ? "carregando…"
        : "—";

  if (forbidden) {
    return (
      <main className="min-h-screen bg-[#0a1828] text-white p-4 md:p-6">
        <div className="mb-6 rounded-md border border-[#e04a4a]/40 bg-[#e04a4a]/10 p-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl">🚫</span>
            <div className="flex-1">
              <h2 className="text-base font-bold text-[#e04a4a]">Acesso restrito</h2>
              <p className="mt-1 text-sm text-[#f3d4d4]">
                Esta tela é restrita ao Dirigente (Presidente/Vice). Solicite acesso ao
                administrador do sistema.
              </p>
              <button
                type="button"
                onClick={() => router.push("/centro-comando")}
                className="mt-3 rounded bg-[#c8a04d] px-4 py-2 text-sm font-semibold text-[#0a1828] transition hover:bg-[#fbbf24]"
              >
                Voltar ao Centro de Comando
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  const chartItems = porDia?.items ?? [];
  const mediaDiaria = porDia?.media_diaria ?? 0;

  return (
    <main className="min-h-screen bg-[#0a1828] text-white p-4 md:p-6" data-testid="bi-page">
      <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eef4]">BI · Inteligência para CCT</h1>
          <p className="mt-1 text-sm text-[#94a8bd]">
            Dados reais para negociar com OGMO e Operadores · última atualização{" "}
            <span key={relativeTick}>{subtitleRelative}</span>
          </p>
        </div>
        <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <BiPeriodSelector value={periodo} onChange={setPeriodo} />
          <button
            type="button"
            onClick={() => void handleDownloadPdf()}
            disabled={downloadingPdf || loading}
            className="rounded bg-[#1a2540] px-4 py-2 text-sm font-medium text-[#e8eef4] ring-1 ring-[#2a5070] transition hover:bg-[#243552] disabled:opacity-50"
          >
            {downloadingPdf ? "Gerando PDF…" : "Exportar PDF"}
          </button>
        </div>
      </header>

      {erro && (
        <div className="mb-4 rounded border border-red-500 bg-red-900/20 px-4 py-2 text-sm text-red-200">
          {erro}
        </div>
      )}

      {loading && !kpis ? (
        <div className="flex h-64 items-center justify-center text-[#94a8bd]">Carregando…</div>
      ) : (
        <>
          {kpis && <BiKpiCards kpis={kpis} periodo={periodo} />}

          <section className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-lg border border-[#2a5070] bg-[#0f2438] p-4 lg:col-span-2">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-[#e8eef4]">
                  📊 {remanejamentosChartHeading(periodo)}
                </h2>
                <span className="shrink-0 rounded bg-[#1a2540] px-2 py-0.5 text-[10px] font-semibold text-[#94a8bd]">
                  MÉDIA {mediaDiaria.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}/DIA
                </span>
              </div>

              <BarChart
                items={chartItems}
                onBarClick={(i) => void handleBarClick(i)}
                height={280}
              />
              <p className="mt-1 text-[10px] text-[#94a8bd]">
                Clique em uma barra para ver o detalhe do dia.
              </p>

              {cards && <BiTopCards cards={cards} />}

              {drillDownDate && (
                <div className="mt-4 rounded border border-[#2a5070] bg-[#0a1828] p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-[#e8eef4]">
                      Drill-down: {drillDownDate}
                    </h3>
                    <button
                      type="button"
                      onClick={fecharDrillDown}
                      className="rounded p-1 text-[#94a8bd] hover:bg-[#1a2540] hover:text-white"
                      aria-label="Fechar drill-down"
                    >
                      ✕
                    </button>
                  </div>

                  {drillDownLoading ? (
                    <p className="text-sm text-[#94a8bd]">Carregando detalhe…</p>
                  ) : drillDownError || (drillDown && drillDown.items.length === 0) ? (
                    <EmptyState
                      icon="📅"
                      title="Sem remanejamentos nesta data"
                      description="Nenhum remanejamento foi registrado nesse dia."
                    />
                  ) : drillDown ? (
                    <>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-[#2a5070] text-left text-[10px] uppercase text-[#94a8bd]">
                            <th className="py-2">SE</th>
                            <th>TPA out</th>
                            <th>Motivo</th>
                            <th>Status</th>
                            <th>Hora</th>
                          </tr>
                        </thead>
                        <tbody>
                          {drillDown.items.map((i) => (
                            <tr key={i.id} className="border-b border-[#1a2540]">
                              <td className="py-1.5 font-mono text-xs text-[#c8a04d]">
                                {i.codigo_se}
                              </td>
                              <td className="text-[#e8eef4]">{i.tpa_out_nome}</td>
                              <td className="text-[#94a8bd]">{i.motivo}</td>
                              <td className="text-[#94a8bd]">{i.status}</td>
                              <td className="text-xs text-[#94a8bd]">
                                {new Date(i.hora_criacao).toLocaleTimeString("pt-BR")}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p className="mt-3 text-xs text-[#94a8bd]">
                        Total: {drillDown.total} remanejamento(s)
                      </p>
                    </>
                  ) : null}
                </div>
              )}
            </div>

            {top && (
              <BiTopRemanejadosColumn
                top={top}
                periodo={periodo}
                primaryInsight={primaryInsight}
              />
            )}
          </section>
        </>
      )}
    </main>
  );
}
