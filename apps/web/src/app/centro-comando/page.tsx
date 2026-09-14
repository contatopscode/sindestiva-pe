// =============================================================================
// SINDESTIVA-PE · /centro-comando — Lousa Espelhada (HU004, Sprint S3)
//
// Mudanças vs S2:
//   - Auto-refresh de 30s pausa enquanto `remanejarCtx !== null`
//     (clearInterval/setInterval controlado por `remanejarCtx` — RR-01).
//   - Placeholder substituído pelo `RemanejamentoModal` real passando
//     `catalogo` (portos, turnos, fainas, funcoes, cells, tpaOptions).
//   - Guard `if (!cell.tpa_id) return;` antes de `setRemanejarCtx` no
//     handler de célula (decisão D04 + RNF-10).
//   - Banner verde de sucesso no TOPO da página com copy
//     "✅ Remanejamento SE-YYYYMMDD-NNN criado" + link discreto para
//     /remanejamentos, auto-hide 6s (D38/D40).
//   - `useEffect` em `remanejarCtx → null` dispara `fetchLousa()`
//     imediato (D39/E17).
//   - `LousaTable` mantém `tabIndex={isEmpty ? -1 : 0}` e
//     `role='gridcell'` condicional ao `cell.tpa_id` (já preparado).
// =============================================================================

"use client";

import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useSearchParams } from "next/navigation";
import type { Porto, Turno } from "@sindestiva/shared";
import { LousaTable } from "./_components/LousaTable";
import { PortoSwitcher } from "./_components/PortoSwitcher";
import { TurnoSwitcher } from "./_components/TurnoSwitcher";
import { SnapshotStatus } from "./_components/SnapshotStatus";
import {
  RemanejamentoModal,
  type RemanejamentoModalCatalogo,
} from "../remanejamentos/_components/RemanejamentoModal";
import {
  getLousaPreview,
  API_URL,
} from "@/lib/api";
import type {
  LousaPreviewResponse,
  TpaOption,
} from "@/lib/tipos";
import type { MotivoRemanejamentoUi } from "@/lib/tipos";

const API_PUBLIC = API_URL;
const SUCCESS_BANNER_MS = 6_000;

/** Lista canônica de motivos (espelha `MotivoRemanejamentoEnum`). */
const MOTIVOS: MotivoRemanejamentoUi[] = [
  "ATESTADO_MEDICO",
  "FALTA_INJUSTIFICADA",
  "REFORCO_TERNO",
  "TROCA_TURNO",
  "ATRASO_15MIN",
  "FALTA_EPI",
  "LIBERACAO_ANTECIPADA",
  "OUTRO",
];

export default function CentroComandoPage(): ReactNode {
  return (
    <Suspense fallback={<div className="loading p-6">Carregando…</div>}>
      <CentroComandoPageInner />
    </Suspense>
  );
}

function CentroComandoPageInner(): ReactNode {
  const [porto, setPorto] = useState<Porto>("SUAPE");
  const [turno, setTurno] = useState<Turno>("DIURNO");
  const [data, setData] = useState<LousaPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [remanejarCtx, setRemanejarCtx] = useState<
    | {
        cell: import("@/lib/tipos").LousaCellOut;
        funcao: import("@/lib/tipos").Funcao;
        faina: import("@/lib/tipos").Faina;
      }
    | null
  >(null);

  // Banner de "forbidden" — feedback do redirect silencioso do middleware.
  const searchParams = useSearchParams();
  const forbiddenPath = searchParams?.get("forbidden");
  const [bannerVisible, setBannerVisible] = useState(true);

  useEffect(() => {
    setBannerVisible(true);
  }, [forbiddenPath]);

  useEffect(() => {
    if (!forbiddenPath) return;
    const id = setTimeout(() => setBannerVisible(false), 8000);
    return () => clearTimeout(id);
  }, [forbiddenPath]);

  // Banner verde de sucesso (HU004/CA05/D40).
  const [successBanner, setSuccessBanner] = useState<{
    codigo_se: string;
    hash_evento: string;
  } | null>(null);

  useEffect(() => {
    if (!successBanner) return;
    const id = setTimeout(() => setSuccessBanner(null), SUCCESS_BANNER_MS);
    return () => clearTimeout(id);
  }, [successBanner]);

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

  // Auto-refresh 30s — pausado enquanto modal aberto (RR-01).
  useEffect(() => {
    if (remanejarCtx !== null) return; // pausa
    const id = setInterval(() => {
      getLousaPreview(porto, turno)
        .then((d) => setData(d))
        .catch(() => {
          /* mantém último snapshot em caso de falha transitória */
        });
    }, 30_000);
    return () => clearInterval(id);
  }, [porto, turno, remanejarCtx]);

  // Refetch imediato ao fechar o modal (E17/D39) — não depende do
  // tick de 30s. O `fetchLousa` é intencionalmente excluído das deps
  // para evitar refetch em mudanças irrelevantes (ele já roda via
  // efeito próprio em [porto, turno]).
  useEffect(() => {
    if (remanejarCtx === null && data !== null) {
      fetchLousa();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remanejarCtx]);

  // Catálogo derivado de `data` para o modal (D16).
  const catalogo: RemanejamentoModalCatalogo = useMemo(() => {
    const tpaMap = new Map<string, TpaOption>();
    for (const c of data?.cells ?? []) {
      if (c.tpa_id && !tpaMap.has(c.tpa_id)) {
        tpaMap.set(c.tpa_id, {
          tpa_id: c.tpa_id,
          tpa_nome: c.tpa_nome ?? "(sem nome)",
          tpa_matricula: c.tpa_matricula ?? null,
        });
      }
    }
    return {
      portos: data?.porto ? [data.porto] : [],
      turnos: data?.turno ? [data.turno] : [],
      fainas: data?.fainas ?? [],
      funcoes: data?.funcoes ?? [],
      cells: data?.cells ?? [],
      tpaOptions: Array.from(tpaMap.values()),
      // lacuna L02-Front: catálogo de CCT ainda não vem do /lousa/public/preview
      cctClausulas: undefined,
    };
  }, [data]);

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

  const turnoSemDados = useMemo(() => {
    if (!data) return false;
    if (data.snapshot.status === "SEM_DADOS") return true;
    return (
      data.stats.total_tpas_escalados === 0 &&
      data.cells.every((c) => !c.tpa_id)
    );
  }, [data]);

  function handleCellClick(
    cell: import("@/lib/tipos").LousaCellOut,
    funcao: import("@/lib/tipos").Funcao,
    faina: import("@/lib/tipos").Faina,
  ) {
    // Guard obrigatório (D04 + RNF-10): descarta cliques em célula
    // sem TPA escalado.
    if (!cell.tpa_id) return;
    setRemanejarCtx({ cell, funcao, faina });
  }

  function handleCloseModal() {
    setRemanejarCtx(null);
  }

  function handleCreated(item: {
    id: string;
    codigo_se: string;
    hash_evento: string;
  }) {
    setSuccessBanner({
      codigo_se: item.codigo_se,
      hash_evento: item.hash_evento,
    });
    // Modal já dispara onClose no fluxo interno; garantimos aqui também.
    setRemanejarCtx(null);
  }

  return (
    <div className="p-6">
      {/* Banner verde de sucesso no TOPO da página (D38/E18) */}
      {successBanner && (
        <div
          role="status"
          aria-live="polite"
          className="mb-4 flex items-start justify-between gap-4 rounded border border-[#5dbb7d]/40 bg-[#5dbb7d]/10 px-4 py-3"
        >
          <div className="text-[12px] text-[#5dbb7d]">
            ✅ Remanejamento{" "}
            <span className="font-mono text-[#d4a574]">{successBanner.codigo_se}</span>{" "}
            criado
            {" · "}
            <a
              href="/remanejamentos"
              className="text-[10px] text-[#5dbb7d] underline-offset-2 hover:underline"
            >
              ver em /remanejamentos
            </a>
          </div>
          <button
            type="button"
            onClick={() => setSuccessBanner(null)}
            className="shrink-0 rounded border border-[#5dbb7d]/40 px-2 py-1 text-[11px] font-semibold text-[#5dbb7d] hover:bg-[#5dbb7d]/20"
            aria-label="Fechar aviso de sucesso"
          >
            ✕
          </button>
        </div>
      )}

      {/* Banner de forbidden — feedback do redirect silencioso do middleware */}
      {forbiddenPath && bannerVisible && (
        <div
          role="alert"
          className="mb-4 flex items-start justify-between gap-4 rounded border border-[#d4a574]/40 bg-[#d4a574]/10 px-4 py-3"
        >
          <div className="text-[12px] text-[#d4a574]">
            🔒 Você não tem permissão para acessar{" "}
            <code className="font-mono">{forbiddenPath}</code> (restrito a{" "}
            {forbiddenPath === "/bi" ? "DIRIGENTE" : "outros perfis"}). Voltar
            ao menu.
          </div>
          <button
            type="button"
            onClick={() => setBannerVisible(false)}
            className="shrink-0 rounded border border-[#d4a574]/40 px-2 py-1 text-[11px] font-semibold text-[#d4a574] hover:bg-[#d4a574]/20"
            aria-label="Fechar aviso"
          >
            ✕
          </button>
        </div>
      )}

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
          {/* KPIs */}
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
                  {data.snapshot.id && data.snapshot.scraped_at
                    ? `${Math.max(1, Math.round((Date.now() - new Date(data.snapshot.scraped_at).getTime()) / 1000))}s`
                    : "—"}
                </div>
                <div className="kpi-delta">Última há alguns segundos</div>
              </div>
            </div>
          )}

          {/* Snapshot status */}
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
            {turnoSemDados && (
              <div className="mt-2 rounded border border-[#d4a574]/40 bg-[#d4a574]/10 px-3 py-2 text-[12px] text-[#d4a574]">
                ℹ️ Scrape concluído, mas o OGMO não publicou TPAs para{" "}
                <strong>{porto}</strong> · <strong>{turno}</strong> nesta data
                (turno vazio — diferente de falha de rede).
              </div>
            )}
            <p className="mt-2 text-[11px] text-[#94a8bd]">
              Matriz de scraping (fonte × porto × turno):{" "}
              <a
                href={`${API_PUBLIC}/api/v1/scraping/status?limit=8`}
                className="font-mono text-[#d4a574] underline-offset-2 hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                GET /api/v1/scraping/status
              </a>
            </p>
          </div>

          {/* Tabela principal */}
          <LousaTable
            fainas={data.fainas}
            funcoes={data.funcoes}
            cells={data.cells}
            onCellClick={handleCellClick}
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

          {/* Footer: timestamp */}
          <div className="mt-3 text-right text-[11px] text-[#94a8bd]">
            Última atualização:{" "}
            <span className="font-mono text-[#d4a574]">
              {new Date().toLocaleTimeString("pt-BR")}
            </span>
          </div>
        </>
      )}

      {/* Modal de remanejamento real (HU001 + HU004) */}
      {remanejarCtx && (
        <RemanejamentoModal
          open={true}
          porto={porto}
          turno={turno}
          catalogo={catalogo}
          motivos={MOTIVOS}
          basesLegais={[]}
          prefill={{
            tpa_id: remanejarCtx.cell.tpa_id ?? undefined,
            faina_id: remanejarCtx.faina.id,
            funcao_id: remanejarCtx.funcao.id,
            data_referencia: remanejarCtx.cell.data_referencia,
            cais_origem: remanejarCtx.cell.cais,
          }}
          onClose={handleCloseModal}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}