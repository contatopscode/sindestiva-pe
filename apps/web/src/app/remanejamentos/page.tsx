// =============================================================================
// SINDESTIVA-PE · /remanejamentos — lista + KPIs (dados reais GET)
// =============================================================================

"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Porto, Turno } from "@sindestiva/shared";
import { getLousaPreview, getRemanejamentos, ApiError } from "@/lib/api";
import { EmptyState } from "@/app/_components/EmptyState";
import { RemanejamentosTable } from "./_components/RemanejamentosTable";
import {
  RemanejamentoModal,
  type RemanejamentoModalCatalogo,
} from "./_components/RemanejamentoModal";
import type {
  LousaPreviewResponse,
  MotivoRemanejamentoUi,
  TpaOption,
} from "@/lib/tipos";
import type { RemanejamentoItemResolved } from "@/lib/api-mappers";
import { computeRemanejamentoKpis } from "@/lib/remanejamento-ui";

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

function dataHojeISO(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function formatSubtitleDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

export default function RemanejamentosPage(): ReactNode {
  const [items, setItems] = useState<RemanejamentoItemResolved[]>([]);
  const [preview, setPreview] = useState<LousaPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const porto: Porto = "SUAPE";
  const turno: Turno = "DIURNO";
  const hojeIso = useMemo(() => dataHojeISO(), []);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const previewData = await getLousaPreview(porto, turno).catch(() => null);
      setPreview(previewData);
      const catalogo = previewData
        ? {
            cells: previewData.cells,
            fainas: previewData.fainas,
            funcoes: previewData.funcoes,
          }
        : undefined;
      const remanejamentos = await getRemanejamentos(
        { skip: 0, limit: 500 },
        catalogo,
      );
      setItems(remanejamentos);
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

  const kpis = useMemo(
    () => computeRemanejamentoKpis(items, hojeIso),
    [items, hojeIso],
  );

  const catalogo: RemanejamentoModalCatalogo = useMemo(() => {
    const cells = preview?.cells ?? [];
    const tpaMap = new Map<string, TpaOption>();
    for (const c of cells) {
      if (c.tpa_id && !tpaMap.has(c.tpa_id)) {
        tpaMap.set(c.tpa_id, {
          tpa_id: c.tpa_id,
          tpa_nome: c.tpa_nome ?? "(sem nome)",
          tpa_matricula: c.tpa_matricula ?? null,
        });
      }
    }
    return {
      portos: preview?.porto ? [preview.porto] : [],
      turnos: preview?.turno ? [preview.turno] : [],
      fainas: preview?.fainas ?? [],
      funcoes: preview?.funcoes ?? [],
      cells,
      tpaOptions: Array.from(tpaMap.values()),
    };
  }, [preview]);

  const subtitleTurno =
    preview?.turno?.nome ?? (turno === "DIURNO" ? "Diurno" : "Noturno");

  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Remanejamentos</h1>
          <p className="section-subtitle">
            Histórico do turno · {formatSubtitleDate(hojeIso)} · {subtitleTurno}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled
            title="Exportação PDF ainda não disponível na API."
            className="cursor-not-allowed rounded border border-[#2a5070] px-4 py-2 text-[12px] font-semibold text-[#5f7a92] opacity-70"
          >
            ⤓ Exportar PDF
          </button>
          <button
            type="button"
            disabled={!preview}
            title={
              preview
                ? undefined
                : "Aguarde o catálogo da lousa para registrar remanejamento."
            }
            onClick={() => setModalOpen(true)}
            className="rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a] disabled:cursor-not-allowed disabled:opacity-50"
          >
            + Novo Remanejamento
          </button>
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
              <div className="kpi-label">Total Hoje</div>
              <div className="kpi-value">{kpis.totalHoje}</div>
              <div className="kpi-delta">registros do dia</div>
            </div>
            <div className="kpi-card green">
              <div className="kpi-label">Aceitos OGMO</div>
              <div className="kpi-value">{kpis.aceitosOgmo}</div>
              <div className="kpi-delta up">
                {kpis.totalHoje > 0
                  ? `${kpis.taxaAceitosPct}% taxa`
                  : "—"}
              </div>
            </div>
            <div className="kpi-card amber">
              <div className="kpi-label">Pendentes</div>
              <div className="kpi-value">{kpis.pendentes}</div>
              <div className="kpi-delta">SLA 5min</div>
            </div>
            <div className="kpi-card red">
              <div className="kpi-label">Recusados</div>
              <div className="kpi-value">{kpis.recusados}</div>
              <div className="kpi-delta down">NACK / cancelados</div>
            </div>
          </div>

          {items.length === 0 ? (
            <EmptyState
              icon="📋"
              title="Nenhum remanejamento registrado"
              description="Quando o fiscal registrar remanejamentos no turno, eles aparecerão aqui com status de notificação ao OGMO."
            />
          ) : (
            <RemanejamentosTable items={items} hojeIso={hojeIso} />
          )}
        </>
      )}

      {modalOpen && preview && (
        <RemanejamentoModal
          open={modalOpen}
          porto={porto}
          turno={turno}
          catalogo={catalogo}
          motivos={MOTIVOS}
          basesLegais={[]}
          onClose={() => setModalOpen(false)}
          onCreated={() => {
            fetchAll();
          }}
          executarENotificarOgmo
        />
      )}
    </div>
  );
}
