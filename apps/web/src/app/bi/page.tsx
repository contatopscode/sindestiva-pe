// =============================================================================
// SINDESTIVA-PE · /bi — BI & Dashboards (Sprint 5 — Marco M5, refinações da M7)
//
// Refactor vs M7:
//   - 403 ROLE_REQUIRED tratado com banner dedicado (H15 — UX do Dirigente
//     não compartilha com erros genéricos). Botão "Voltar ao Centro de
//     Comando" usa router.push('/centro-comando').
//   - EmptyState genérico substituído por "Sem remanejamentos no período"
//     com ícone 📊 quando `porDia.total === 0`.
//   - Drill-down deixou de ser modal: renderizado INLINE como expansão
//     abaixo do gráfico clicado (sem nova rota, sem overlay). 404 →
//     EmptyState "Sem remanejamentos nesta data".
//   - Auto-refresh a cada 5 min (CACHE_TTL_SEGUNDOS do backend) com
//     indicador "Atualizado às HH:MM" no topo da página.
//   - Tabs horizontais '7d · 30d · 90d · 365d' (default 30d) usando o
//     `PeriodoDias` de `@/lib/tipos`.
//
// Restrição: apenas DIRIGENTE (RBAC do backend retorna 403 com
// `detail.code === "ROLE_REQUIRED"`).
// ============================================================================

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

const PERIODOS: { value: PeriodoDias; label: string }[] = [
  { value: 7, label: "7d" },
  { value: 30, label: "30d" },
  { value: 90, label: "90d" },
  { value: 365, label: "365d" },
];

/** TTL de auto-refresh: 5 min (espelha CACHE_TTL_SEGUNDOS=300 do backend). */
const AUTO_REFRESH_MS = 5 * 60 * 1000;

// Formatadores.
const brl = (v: number): string =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const pct = (v: number): string => `${v.toFixed(1)}%`;

/** Formatador de horário HH:MM para o indicador "Atualizado às …". */
function formatHoraAgora(d: Date): string {
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

/**
 * Tenta extrair `code` de um `ApiError.detail` que o backend serializou
 * como string JSON (caso `detail` seja objeto) — `apiFetch` faz
 * `JSON.stringify` quando o detail não é string. Mantém fallback para
 * a string crua, preservando mensagens legíveis em outros cenários.
 */
function extractDetailCode(detail: string): { code?: string; message: string } {
  const trimmed = detail.trim();
  if (trimmed.startsWith("{")) {
    try {
      const obj = JSON.parse(trimmed) as { code?: unknown; message?: unknown };
      if (typeof obj.code === "string" && typeof obj.message === "string") {
        return { code: obj.code, message: obj.message };
      }
    } catch {
      /* fallback: detail é texto livre */
    }
  }
  return { message: detail };
}

export default function BIPage(): ReactNode {
  const router = useRouter();

  const [periodo, setPeriodo] = useState<PeriodoDias>(30);
  const [kpis, setKpis] = useState<BIKpis | null>(null);
  const [porDia, setPorDia] = useState<RemanejamentosPorDia | null>(null);
  const [top, setTop] = useState<TopRemanejados | null>(null);
  const [cards, setCards] = useState<TopCards | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [drillDown, setDrillDown] = useState<DrillDown | null>(null);
  const [drillDownDate, setDrillDownDate] = useState<string | null>(null);
  const [drillDownError, setDrillDownError] = useState<boolean>(false);
  const [drillDownLoading, setDrillDownLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  /** Bloqueio total da UI quando o backend diz 403 ROLE_REQUIRED. */
  const [forbidden, setForbidden] = useState<{
    code: string;
    message: string;
  } | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<Date | null>(null);

  const loadAll = useCallback(async (p: PeriodoDias): Promise<void> => {
    setLoading(true);
    setErro(null);
    setForbidden(null);
    try {
      const [k, d, t, c, i] = await Promise.all([
        getBIKpis(p),
        getBIRemanejamentosPorDia(p),
        getBITopRemanejados(p, 10),
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

  // Carrega ao montar e quando o período muda.
  useEffect(() => {
    void loadAll(periodo);
  }, [periodo, loadAll]);

  // Auto-refresh a cada 5 min — bate com CACHE_TTL_SEGUNDOS do Redis.
  // Usa ref para evitar reiniciar o intervalo a cada re-render.
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

  // Banner dedicado de 403 ROLE_REQUIRED — tela inteira bloqueada.
  if (forbidden) {
    return (
      <main className="min-h-screen bg-[#0a1828] text-white p-4 md:p-6">
        <div className="mb-6 rounded-md border border-[#e04a4a]/40 bg-[#e04a4a]/10 p-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl">🚫</span>
            <div className="flex-1">
              <h2 className="text-base font-bold text-[#e04a4a]">
                Acesso restrito
              </h2>
              <p className="mt-1 text-sm text-[#f3d4d4]">
                Esta tela é restrita ao Dirigente (Presidente/Vice). Solicite
                acesso ao administrador do sistema.
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

  // EmptyState específico quando porDia.total === 0 (H15).
  if (!loading && porDia && porDia.total === 0) {
    return (
      <main className="min-h-screen bg-[#0a1828] text-white p-4 md:p-6">
        <header className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#e8eef4]">BI & Dashboards</h1>
            {kpis && (
              <p className="text-sm text-[#94a8bd]">
                Período: {kpis.periodo_inicio} → {kpis.periodo_fim}
              </p>
            )}
            {ultimaAtualizacao && (
              <p className="mt-1 text-[11px] text-[#94a8bd]">
                Atualizado às {formatHoraAgora(ultimaAtualizacao)} · auto-refresh em 5 min
              </p>
            )}
          </div>
          <PeriodoSelector value={periodo} onChange={setPeriodo} />
        </header>
        <EmptyState
          icon="📊"
          title="Sem remanejamentos no período"
          description={`Não há remanejamentos registrados nos últimos ${periodo} dias. Selecione outro período ou aguarde o início das operações.`}
        />
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0a1828] text-white p-4 md:p-6">
      <header className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eef4]">BI & Dashboards</h1>
          {kpis && (
            <p className="text-sm text-[#94a8bd]">
              Período: {kpis.periodo_inicio} → {kpis.periodo_fim}
            </p>
          )}
          {ultimaAtualizacao && (
            <p className="mt-1 text-[11px] text-[#94a8bd]">
              Atualizado às {formatHoraAgora(ultimaAtualizacao)} · auto-refresh em 5 min
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <PeriodoSelector value={periodo} onChange={setPeriodo} />
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={downloadingPdf || loading}
            className="rounded bg-[#c8a04d] px-4 py-2 text-sm font-semibold text-[#0a1828] transition hover:bg-[#fbbf24] disabled:opacity-50"
          >
            {downloadingPdf ? "Gerando PDF..." : "📄 Exportar PDF"}
          </button>
        </div>
      </header>

      {erro && (
        <div className="mb-4 rounded border border-red-500 bg-red-900/20 px-4 py-2 text-sm text-red-200">
          ❌ {erro}
        </div>
      )}

      {loading ? (
        <div className="flex h-64 items-center justify-center text-[#94a8bd]">Carregando…</div>
      ) : (
        <>
          {/* 1. KPIs (T7-01) */}
          {kpis && (
            <section className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <KpiCard
                label="Comparecimento"
                value={pct(kpis.comparecimento.percentual)}
                detail={`${kpis.comparecimento.total_confirmados}/${kpis.comparecimento.total_escalados} TPAs`}
                tone="gold"
              />
              <KpiCard
                label="Folha paga"
                value={brl(kpis.folha_paga.valor_total_brl)}
                detail={`${kpis.folha_paga.total_remanejamentos} remanejamentos`}
                tone="cyan"
              />
              <KpiCard
                label="Causa #1 falta"
                value={kpis.causa_principal_falta.motivo}
                detail={`${kpis.causa_principal_falta.total} (${pct(kpis.causa_principal_falta.percentual)})`}
                tone="amber"
              />
              <KpiCard
                label="% NACK (OGMO)"
                value={pct(kpis.percentual_nack.percentual)}
                detail={`${kpis.percentual_nack.total_nack}/${kpis.percentual_nack.total_notificados} notificações`}
                tone={kpis.percentual_nack.percentual > 10 ? "red" : "green"}
              />
            </section>
          )}

          {/* 2. Gráfico + Top remanejados */}
          <section className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-lg border border-[#2a5070] bg-[#0f2438] p-4 lg:col-span-2">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-[#e8eef4]">
                  Remanejamentos por dia
                </h2>
                {porDia && (
                  <span className="text-xs text-[#94a8bd]">
                    {porDia.total} no período · {porDia.media_diaria}/dia
                  </span>
                )}
              </div>
              {porDia && <BarChart items={porDia.items} onBarClick={(i) => void handleBarClick(i)} />}
              <p className="mt-2 text-xs text-[#94a8bd]">
                💡 Clique em uma barra para ver o detalhe do dia.
              </p>

              {/* Drill-down expandido inline (sem modal). */}
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
                  ) : drillDownError ? (
                    <EmptyState
                      icon="📅"
                      title="Sem remanejamentos nesta data"
                      description="Nenhum remanejamento foi registrado nesse dia."
                    />
                  ) : drillDown && drillDown.items.length === 0 ? (
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

            <div className="rounded-lg border border-[#2a5070] bg-[#0f2438] p-4">
              <h2 className="mb-3 text-lg font-semibold text-[#e8eef4]">
                Top remanejados
              </h2>
              {top && top.items.length > 0 ? (
                <ol className="space-y-2">
                  {top.items.map((t, idx) => (
                    <li
                      key={t.tpa_id}
                      className="flex items-center justify-between border-b border-[#1a2540] pb-1.5 text-sm"
                    >
                      <span className="flex items-center gap-2">
                        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[#c8a04d] text-[10px] font-bold text-[#0a1828]">
                          {idx + 1}
                        </span>
                        <span>
                          <span className="text-[#e8eef4]">{t.tpa_nome}</span>
                          {t.tpa_matricula && (
                            <span className="ml-2 text-xs text-[#94a8bd]">
                              {t.tpa_matricula}
                            </span>
                          )}
                        </span>
                      </span>
                      <span className="font-mono text-sm font-semibold text-[#c8a04d]">
                        {t.total_remanejamentos}×
                      </span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-sm text-[#94a8bd]">Sem dados no período.</p>
              )}
            </div>
          </section>

          {/* 3. Top cards + Insights */}
          <section className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
            {cards && (
              <>
                <TopCardBox
                  titulo="Função + remanejada"
                  card={cards.funcao_mais_remanejada}
                />
                <TopCardBox
                  titulo="Cais + problemático"
                  card={cards.cais_mais_problematico}
                />
                <TopCardBox
                  titulo="Horário + crítico"
                  card={cards.horario_mais_critico}
                />
              </>
            )}
          </section>

          {insights && insights.items.length > 0 && (
            <section className="mb-6">
              <h2 className="mb-3 text-lg font-semibold text-[#e8eef4]">
                Insights automáticos
              </h2>
              <ul className="space-y-2">
                {insights.items.map((ins, idx) => (
                  <li
                    key={idx}
                    className={`rounded border-l-4 px-4 py-2 text-sm ${
                      ins.severidade === "critico"
                        ? "border-red-500 bg-red-900/20"
                        : ins.severidade === "alerta"
                          ? "border-amber-500 bg-amber-900/20"
                          : "border-blue-500 bg-blue-900/20"
                    }`}
                  >
                    <span className="mr-2 font-mono text-[10px] uppercase text-[#94a8bd]">
                      [{ins.severidade}]
                    </span>
                    {ins.mensagem}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Subcomponentes
// ---------------------------------------------------------------------------


function PeriodoSelector({
  value,
  onChange,
}: {
  value: PeriodoDias;
  onChange: (p: PeriodoDias) => void;
}): ReactNode {
  return (
    <div className="flex gap-1 rounded border border-[#2a5070] bg-[#0f2438] p-0.5 text-xs">
      {PERIODOS.map((p) => (
        <button
          key={p.value}
          type="button"
          onClick={() => onChange(p.value)}
          aria-pressed={value === p.value}
          className={`rounded px-3 py-1 transition ${
            value === p.value
              ? "bg-[#c8a04d] font-semibold text-[#0a1828]"
              : "text-[#94a8bd] hover:text-[#e8eef4]"
          }`}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

function KpiCard({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "gold" | "cyan" | "amber" | "green" | "red";
}): ReactNode {
  const toneClass: Record<typeof tone, string> = {
    gold: "border-[#c8a04d] bg-[#0f2438]",
    cyan: "border-cyan-500 bg-[#0f2438]",
    amber: "border-amber-500 bg-[#0f2438]",
    green: "border-green-500 bg-[#0f2438]",
    red: "border-red-500 bg-[#0f2438]",
  };
  return (
    <div className={`rounded-lg border-l-4 p-4 ${toneClass[tone]}`}>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-[#94a8bd]">
        {label}
      </div>
      <div className="mt-1 text-2xl font-bold text-[#e8eef4]">{value}</div>
      <div className="mt-0.5 text-xs text-[#94a8bd]">{detail}</div>
    </div>
  );
}

function TopCardBox({
  titulo,
  card,
}: {
  titulo: string;
  card: { label: string; total: number; percentual: number } | null;
}): ReactNode {
  return (
    <div className="rounded-lg bg-[#1a2540] p-4 text-white">
      <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[#c8a04d]">
        {titulo}
      </h3>
      {card ? (
        <>
          <p className="mt-2 text-xl font-bold">{card.label}</p>
          <p className="text-xs text-[#94a8bd]">
            {card.total} remanejamentos · {pct(card.percentual)}
          </p>
        </>
      ) : (
        <p className="mt-2 text-sm italic text-[#94a8bd]">Sem dados</p>
      )}
    </div>
  );
}
