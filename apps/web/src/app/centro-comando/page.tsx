// =============================================================================
// SINDESTIVA-PE · /centro-comando — Lousa Espelhada (tela principal)
//
// Réplica fiel do protótipo (SINDESTIVA-PE-PROTOTIPO.html, sec-lousa).
// Stack atual: client component + fetch + auto-refresh 30s + mock fallback.
// Sprint 4 (T4-01..T4-10 do plano v1.0).
//
// O que ainda NÃO está aqui (todas as pendências registradas no fim do
// arquivo):
//   - WebSocket (T4-05) — só Sprint 3 do 45d (PWA + WS)
//   - Toast notifications (T4-07)
//   - Filtros e busca (T4-09)
//   - Banner "Sync paused" (T4-10)
//   - Modal de remanejamento completo (T5-02) — placeholder abaixo
// =============================================================================

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Porto, Turno } from "@sindestiva/shared";
import { LousaTable } from "./_components/LousaTable";
import { PortoSwitcher } from "./_components/PortoSwitcher";
import { TurnoSwitcher } from "./_components/TurnoSwitcher";
import { SnapshotStatus } from "./_components/SnapshotStatus";
import { getLousaPreview } from "@/lib/api";
import type { LousaCellOut, LousaPreviewResponse, Funcao, Faina } from "@/lib/tipos";

export default function CentroComandoPage(): ReactNode {
  const [porto, setPorto] = useState<Porto>("SUAPE");
  const [turno, setTurno] = useState<Turno>("DIURNO");
  const [data, setData] = useState<LousaPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [remanejarCtx, setRemanejarCtx] = useState<
    { cell: LousaCellOut; funcao: Funcao; faina: Faina } | null
  >(null);

  const fetchLousa = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await getLousaPreview(porto, turno);
      setData(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [porto, turno]);

  useEffect(() => {
    fetchLousa();
  }, [fetchLousa]);

  // Auto-refresh 30s — T4-05 (WebSocket) substitui isto.
  useEffect(() => {
    const id = setInterval(() => {
      getLousaPreview(porto, turno).then(setData).catch(() => {});
    }, 30_000);
    return () => clearInterval(id);
  }, [porto, turno]);

  // KPIs (do protótipo, sec-lousa linhas 1282-1305).
  const kpis = useMemo(() => {
    if (!data) return null;
    const totalCells = data.stats.total_cells;
    const totalTpas = data.stats.total_tpas_escalados;
    const ausentes = data.cells.filter((c) => c.status === "AUSENTE").length;
    const remanejados = data.cells.filter((c) => c.status === "REMANEJADO").length;
    const confirmados = data.cells.filter((c) => c.status === "CONFIRMADO").length;
    const presenca = totalCells > 0 ? Math.round(((totalCells - ausentes) / totalCells) * 100) : 0;
    return { totalTpas, ausentes, remanejados, confirmados, presenca };
  }, [data]);

  return (
    <div className="p-6">
      {/* Cabeçalho da seção */}
      <div className="section-header">
        <div>
          <h1 className="section-title">
            Lousa Espelhada — Porto de {data?.porto.codigo ?? porto}
          </h1>
          <p className="section-subtitle">
            Réplica da lousa oficial OGMO/PE · Turno {data?.turno.nome ?? turno}
            {data?.snapshot.scraped_at &&
              ` · Scrape ${new Date(data.snapshot.scraped_at).toLocaleString("pt-BR")}`}
          </p>
        </div>
        <div className="controls flex items-center gap-2">
          <PortoSwitcher value={porto} onChange={setPorto} />
          <TurnoSwitcher value={turno} onChange={setTurno} />
        </div>
      </div>

      {/* Erro fatal */}
      {error && (
        <div className="error-box mb-4">
          ❌ Erro ao buscar lousa: <strong>{error}</strong>
        </div>
      )}

      {/* Loading inicial */}
      {loading && !data && (
        <div className="loading">Carregando lousa de <code>127.0.0.1:8000</code>…</div>
      )}

      {data && (
        <>
          {/* KPIs (réplica T4-01) */}
          {kpis && (
            <div className="kpi-row">
              <div className="kpi-card">
                <div className="kpi-label">TPAs Escalados</div>
                <div className="kpi-value">{kpis.totalTpas}</div>
                <div className="kpi-delta">↑ Snapshot atual</div>
              </div>
              <div className="kpi-card green">
                <div className="kpi-label">Presença</div>
                <div className="kpi-value">{kpis.presenca}%</div>
                <div className="kpi-delta">
                  {kpis.confirmados} confirmados · {kpis.ausentes} ausentes
                </div>
              </div>
              <div className="kpi-card amber">
                <div className="kpi-label">Remanejamentos Hoje</div>
                <div className="kpi-value">{kpis.remanejados}</div>
                <div className="kpi-delta">No snapshot atual</div>
              </div>
              <div className="kpi-card cyan">
                <div className="kpi-label">Sync OGMO</div>
                <div className="kpi-value">
                  {data.snapshot.id ? `${Math.max(1, Math.round((Date.now() - new Date(data.snapshot.scraped_at ?? 0).getTime()) / 1000))}s` : "—"}
                </div>
                <div className="kpi-delta">Última há alguns segundos</div>
              </div>
            </div>
          )}

          {/* Snapshot status (T4-10 — banner "Sync paused" se status=ERRO) */}
          <div className="mb-4">
            <SnapshotStatus
              snapshot={data.snapshot}
              onRefresh={fetchLousa}
              loading={loading}
            />
            {data.snapshot.status === "ERRO" && (
              <div className="mt-2 rounded border border-[#e8a33d]/40 bg-[#e8a33d]/10 px-3 py-2 text-[12px] text-[#e8a33d]">
                ⚠️ Sync paused — scraper reportou erro: {data.snapshot.erro_detalhes ?? "(sem detalhes)"}
              </div>
            )}
            {data.snapshot.status === "LAYOUT_MUDOU" && (
              <div className="mt-2 rounded border border-[#9b7ec4]/40 bg-[#9b7ec4]/10 px-3 py-2 text-[12px] text-[#9b7ec4]">
                🔧 Layout da TPA/OGMO mudou — fingerprint divergente. Verificar
                scraper (Risco R2 do plano v1.0).
              </div>
            )}
          </div>

          {/* Tabela principal (T4-02) */}
          <LousaTable
            fainas={data.fainas}
            funcoes={data.funcoes}
            cells={data.cells}
            onCellClick={(cell, funcao, faina) => setRemanejarCtx({ cell, funcao, faina })}
          />

          {/* Legenda */}
          <div className="lousa-legend">
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: "var(--cat-mando)" }} />
              Mando (6)
            </div>
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: "var(--cat-terno)" }} />
              Terno (6)
            </div>
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: "var(--cat-tecnica)" }} />
              Técnica (12)
            </div>
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: "var(--cat-vigia)" }} />
              Vigia (2)
            </div>
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: "rgba(224,74,74,0.3)", border: "1px solid var(--accent-red)" }} />
              Ausente
            </div>
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: "rgba(232,163,61,0.3)", border: "1px solid var(--accent-amber)" }} />
              Remanejado
            </div>
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: "rgba(93,187,125,0.3)", border: "1px solid var(--accent-green)" }} />
              Confirmado
            </div>
            <div className="legend-item" style={{ marginLeft: "auto" }}>
              <div className="legend-swatch" style={{ background: "var(--accent-gold)" }} />
              {data.fainas.length} fainas × {data.funcoes.length} funções
            </div>
          </div>

          {/* Footer: timestamp + ação "Atualizar" */}
          <div className="mt-3 text-right text-[11px] text-[#94a8bd]">
            Última atualização:{" "}
            <span className="font-mono text-[#d4a574]">
              {new Date().toLocaleTimeString("pt-BR")}
            </span>
          </div>
        </>
      )}

      {/* Modal de remanejamento placeholder (Sprint 5 T5-02) */}
      {remanejarCtx && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4"
          onClick={() => setRemanejarCtx(null)}
        >
          <div
            className="w-full max-w-md rounded-lg border border-[#2a5070] bg-[#0a1929] p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-1 text-lg font-bold text-[#e8eef4]">
              Remanejar TPA
            </h2>
            <p className="mb-4 text-[12px] text-[#94a8bd]">
              Modal pré-preenchido — implementação completa em Sprint 5 (T5-02).
            </p>
            <dl className="mb-4 grid grid-cols-[110px_1fr] gap-y-2 text-[12px]">
              <dt className="text-[#94a8bd]">TPA a remover</dt>
              <dd className="font-mono">
                {remanejarCtx.cell.tpa_matricula} · {remanejarCtx.cell.tpa_nome ?? "—"}
              </dd>
              <dt className="text-[#94a8bd]">Função</dt>
              <dd>{remanejarCtx.funcao.nome}</dd>
              <dt className="text-[#94a8bd]">Faina</dt>
              <dd>{remanejarCtx.faina.nome}</dd>
              <dt className="text-[#94a8bd]">Cais</dt>
              <dd className="font-mono">{remanejarCtx.cell.cais ?? "—"}</dd>
              <dt className="text-[#94a8bd]">Data</dt>
              <dd className="font-mono">{remanejarCtx.cell.data_referencia}</dd>
            </dl>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setRemanejarCtx(null)}
                className="rounded border border-[#2a5070] px-4 py-2 text-[12px] font-semibold text-[#94a8bd] hover:text-[#e8eef4]"
              >
                Fechar
              </button>
              <a
                href={`/remanejamentos/novo?tpa=${remanejarCtx.cell.tpa_id ?? ""}&faina=${remanejarCtx.faina.codigo}&funcao=${remanejarCtx.funcao.codigo}`}
                className="rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a]"
              >
                Abrir formulário completo
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
