// =============================================================================
// SINDESTIVA-PE · /remanejamentos/novo (HU003, Sprint S3)
//
// Mudanças vs S2:
//   - Carrega `getLousaPreview(porto, turno)` antes de montar o `prefill`
//     (D17 + D37).
//   - Resolve o param `tpa` por regex `/^[0-9a-f-]{36}$/i`: UUID vai
//     direto para `tpa_id`; matrícula OGMO é localizada em
//     `cells[].tpa_matricula` (D17).
//   - Resolve os params `faina` e `funcao` por código via
//     `catalogo.fainas`/`catalogo.funcoes`.
//   - Modo "sem prefill" (sem query params) abre com selects livres
//     (HU003/RN04 — defaults `data_referencia=hoje`, `porto=SUAPE`,
//     `turno=DIURNO`).
//   - Mantém `<Suspense fallback='Carregando…'>` (Next 15, RR-11).
// =============================================================================

"use client";

import {
  Suspense,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useSearchParams } from "next/navigation";
import type { Porto, Turno } from "@sindestiva/shared";
import {
  RemanejamentoModal,
  type RemanejamentoModalCatalogo,
  type RemanejamentoModalPrefill,
} from "../_components/RemanejamentoModal";
import { getLousaPreview, ApiError } from "@/lib/api";
import type {
  LousaPreviewResponse,
  MotivoRemanejamentoUi,
  TpaOption,
} from "@/lib/tipos";

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

const REGEX_UUID = /^[0-9a-f-]{36}$/i;

function dataHojeISO(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function NovoRemanejamentoContent(): ReactNode {
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(true);
  const [userEmail, setUserEmail] = useState<string>("—");
  const [preview, setPreview] = useState<LousaPreviewResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(true);

  // Defaults: data = hoje, porto = SUAPE, turno = DIURNO.
  const portoParam = searchParams?.get("porto");
  const turnoParam = searchParams?.get("turno");
  const porto: Porto =
    portoParam === "RECIFE" || portoParam === "SUAPE" ? portoParam : "SUAPE";
  const turno: Turno =
    turnoParam === "NOTURNO" || turnoParam === "DIURNO" ? turnoParam : "DIURNO";

  // Carrega `getLousaPreview` antes de montar o `prefill` (HU003/CA01).
  useEffect(() => {
    let cancelled = false;
    setLoadingPreview(true);
    setLoadError(null);
    getLousaPreview(porto, turno)
      .then((d) => {
        if (cancelled) return;
        setPreview(d);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? err.detail
            : err instanceof Error
              ? err.message
              : "Erro ao carregar lousa.";
        setLoadError(msg);
      })
      .finally(() => {
        if (cancelled) return;
        setLoadingPreview(false);
      });
    return () => {
      cancelled = true;
    };
  }, [porto, turno]);

  useEffect(() => {
    fetch("/api/auth/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) setUserEmail(d.email ?? "—");
      })
      .catch(() => undefined);
  }, []);

  const tpaParam = searchParams?.get("tpa") ?? "";
  const fainaParam = searchParams?.get("faina") ?? "";
  const funcaoParam = searchParams?.get("funcao") ?? "";

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
      cctClausulas: undefined,
    };
  }, [preview]);

  const prefill: RemanejamentoModalPrefill | undefined = useMemo(() => {
    if (!preview) return undefined;

    // TPA: UUID direto OU matrícula via `cells[].tpa_matricula` (D37).
    let tpaId: string | undefined;
    if (tpaParam) {
      if (REGEX_UUID.test(tpaParam)) {
        tpaId = tpaParam;
      } else {
        const cell = preview.cells.find(
          (c) => c.tpa_matricula === tpaParam,
        );
        tpaId = cell?.tpa_id ?? undefined;
      }
    }

    // Faina: por código do catálogo.
    const fainaId = fainaParam
      ? preview.fainas.find((f) => f.codigo === fainaParam)?.id
      : undefined;

    // Função: por código do catálogo.
    const funcaoId = funcaoParam
      ? preview.funcoes.find((f) => f.codigo === funcaoParam)?.id
      : undefined;

    if (!tpaId && !fainaId && !funcaoId) return undefined;

    return {
      tpa_id: tpaId,
      faina_id: fainaId,
      funcao_id: funcaoId,
      data_referencia: dataHojeISO(),
    };
  }, [preview, tpaParam, fainaParam, funcaoParam]);

  if (!open) {
    return (
      <div className="p-6">
        <div className="section-header">
          <div>
            <h1 className="section-title">Novo Remanejamento</h1>
            <p className="section-subtitle">Modal fechado.</p>
          </div>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a]"
          >
            Abrir formulário
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Novo Remanejamento</h1>
          <p className="section-subtitle">
            Operador:{" "}
            <span className="font-mono text-[#d4a574]">{userEmail}</span>{" "}
            · Porto {porto} · Turno {turno}
          </p>
        </div>
      </div>

      {loadingPreview && (
        <div className="loading">Carregando catálogo da lousa…</div>
      )}

      {loadError && (
        <div className="login-error" role="alert">
          ⚠ Falha ao carregar lousa: {loadError}. O modal abrirá em modo
          &quot;sem prefill&quot;.
        </div>
      )}

      {!loadingPreview && preview && (
        <RemanejamentoModal
          open={true}
          porto={porto}
          turno={turno}
          catalogo={catalogo}
          motivos={MOTIVOS}
          basesLegais={[]}
          prefill={prefill}
          onCreated={() => {
            setOpen(false);
          }}
          onClose={() => setOpen(false)}
        />
      )}
    </div>
  );
}

export default function NovoRemanejamentoPage(): ReactNode {
  return (
    <Suspense fallback={<div className="loading">Carregando…</div>}>
      <NovoRemanejamentoContent />
    </Suspense>
  );
}