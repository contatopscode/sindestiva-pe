// =============================================================================
// SINDESTIVA-PE · RemanejamentoModal — modal pré-preenchido para novo
// remanejamento (HU001 + HU003 + HU004, Sprint S3).
//
// Mudanças vs S2:
//   - Props ampliadas com `catalogo` (portos/turnos/fainas/funcoes/cells/
//     tpaOptions/cctClausulas) — resolvem UUIDs do payload
//     `RemanejamentoBase`.
//   - `MOTIVOS`/`BASES_LEGAIS` hardcoded substituídos pelo enum
//     `MotivoRemanejamentoUi` (via prop) e pela lista de `CctClausula`
//     do catálogo.
//   - `tpa_in_id` via `<select>` em `tpaOptions`; `cais_origem` via
//     `<input maxLength={8}>`.
//   - `data_referencia` via `<input type='date' min={hoje-7d} max={hoje}>`.
//   - Contadores `NNN/1000`, `NNN/500`, `NNN/2000` para os campos
//     `motivo_outro_texto`, `base_legal_texto_livre` e `observacoes`.
//   - Toggle "Não achei no catálogo" revela `<textarea>` de base legal
//     mutuamente exclusivo com o select de CCT.
//   - Fechamento via Esc/clique no backdrop bloqueado enquanto
//     `submitting=true` (E4).
//   - Estado de sucesso exibe `codigo_se` + `hash_evento` por 1,5s antes
//     de fechar.
//   - 404 `TPA_OUT_NOT_FOUND` → mensagem inline e modal permanece aberto.
//   - `aria-modal='true'`, `role='dialog'`, `aria-labelledby='reman-modal-title'`.
//   - Payload casa com `RemanejamentoBase` Pydantic (sem `notify_pwa`/`ack_cct`).
// =============================================================================

"use client";

import {
  useEffect,
  useMemo,
  useState,
  type ReactNode,
  type FormEvent,
} from "react";
import type { Porto, Turno } from "@sindestiva/shared";
import {
  ApiError,
  aprovarRemanejamento,
  createRemanejamento,
  notifyOgmo,
} from "@/lib/api";
import { labelPendenciaTpaOut } from "@/lib/remanejamento-modal-validation";
import { labelForMotivo } from "@/lib/remanejamento-ui";
import { StatusBadge } from "@/app/_components/StatusBadge";
import type {
  CctClausula,
  Faina,
  Funcao,
  LousaCellOut,
  MotivoRemanejamentoUi,
  PortoOut,
  RemanejamentoCreate,
  TpaOption,
  TurnoOut,
} from "@/lib/tipos";

const MAX_MOTIVO_OUTRO = 1000;
const MAX_BASE_LEGAL_LIVRE = 500;
const MAX_OBSERVACOES = 2000;
const SUCCESS_HOLD_MS = 1500;
const MSG_TPA_OUT_NAO_ENCONTRADO =
  "TPA não encontrado. Atualize a lousa e tente novamente.";

/**
 * Catálogo necessário para preencher o modal de remanejamento com UUIDs
 * reais (HU001/CA01..CA06). Vem de `getLousaPreview` + endpoint de CCT
 * (lacuna L02-Front — opcional).
 */
export interface RemanejamentoModalCatalogo {
  portos: PortoOut[];
  turnos: TurnoOut[];
  fainas: Faina[];
  funcoes: Funcao[];
  cells: LousaCellOut[];
  tpaOptions: TpaOption[];
  /** Catálogo de CCT — quando ausente, modal já abre com textarea. */
  cctClausulas?: CctClausula[];
}

export interface RemanejamentoModalPrefill {
  /** UUID do TPA a remover (resolvido pelo caller). */
  tpa_id?: string;
  /** UUID da faina — pré-preenchido pelo caller (centro-comando). */
  faina_id?: string;
  /** UUID da função — pré-preenchido pelo caller. */
  funcao_id?: string;
  /** Data de referência inicial (YYYY-MM-DD). Default = hoje. */
  data_referencia?: string;
  /** Texto livre inicial do `cais_origem`. */
  cais_origem?: string | null;
}

export interface RemanejamentoModalProps {
  /** Controla visibilidade do modal (default = true). */
  open?: boolean;
  /** Callback para fechar. Bloqueado enquanto `submitting=true`. */
  onClose: () => void;
  /** Callback disparado após criação bem-sucedida (modal já fechou). */
  onCreated?: (item: { id: string; codigo_se: string; hash_evento: string }) => void;
  /** Pré-preenchimento vindo do clique na lousa (opcional). */
  prefill?: RemanejamentoModalPrefill;
  /** Catálogo carregado pelo caller (centro-comando ou /novo). */
  catalogo: RemanejamentoModalCatalogo;
  /** Porto atual — selecionado pelo caller. */
  porto: Porto;
  /** Turno atual — selecionado pelo caller. */
  turno: Turno;
  /** Lista de motivos (espelha `MotivoRemanejamentoEnum`). */
  motivos: MotivoRemanejamentoUi[];
  /** Lista de cláusulas CCT — vazia = sem catálogo (textarea visível). */
  basesLegais: CctClausula[];
  /** Quando true, encadeia createRemanejamento + aprovarRemanejamento + notifyOgmo (atômico). Rota /remanejamentos passa true (botão do protótipo); rota /remanejamentos/novo deixa false (default, só criar). Bifurcação deliberada — vide decisão D06 no plano SINDESTIVA-PE-FSW-2026-004. */
  executarENotificarOgmo?: boolean;
}

function dataHojeISO(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function dataOffsetISO(dias: number): string {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function RemanejamentoModal({
  open = true,
  prefill,
  onCreated,
  onClose,
  catalogo,
  porto,
  turno,
  motivos,
  basesLegais,
  executarENotificarOgmo = false,
}: RemanejamentoModalProps): ReactNode | null {
  const hoje = useMemo(() => dataHojeISO(), []);
  const minData = useMemo(() => dataOffsetISO(-7), []);
  const maxData = hoje;

  // Resoluções UUID a partir de porto/turno e prefill.
  const portoId = useMemo(
    () => catalogo.portos.find((p) => p.codigo === porto)?.id ?? "",
    [catalogo.portos, porto],
  );
  const turnoId = useMemo(
    () => catalogo.turnos.find((t) => t.codigo === turno)?.id ?? "",
    [catalogo.turnos, turno],
  );

  const [motivo, setMotivo] = useState<MotivoRemanejamentoUi>(
    motivos[0] ?? "OUTRO",
  );
  const [motivoOutro, setMotivoOutro] = useState<string>("");
  const [caisOrigem, setCaisOrigem] = useState<string>(prefill?.cais_origem ?? "");
  const [dataReferencia, setDataReferencia] = useState<string>(
    prefill?.data_referencia ?? hoje,
  );
  const [funcaoId, setFuncaoId] = useState<string>(prefill?.funcao_id ?? "");
  const [fainaId, setFainaId] = useState<string>(prefill?.faina_id ?? "");

  // Base legal: select CCT + textarea mutuamente exclusivos. Quando
  // `basesLegais` chega vazio, textarea já é a opção default.
  const [baseLegalMode, setBaseLegalMode] = useState<"catalogo" | "livre">(
    basesLegais.length > 0 ? "catalogo" : "livre",
  );
  const [baseLegalCctId, setBaseLegalCctId] = useState<string>(
    basesLegais[0]?.id ?? "",
  );
  const [baseLegalLivre, setBaseLegalLivre] = useState<string>("");

  const [observacoes, setObservacoes] = useState<string>("");
  const [anexoUrl, setAnexoUrl] = useState<string>("");
  const [tpaOutMatricula, setTpaOutMatricula] = useState<string>("");
  const [tpaInMatricula, setTpaInMatricula] = useState<string>("");
  const [confirmCct, setConfirmCct] = useState<boolean>(false);
  const [notifyPwa, setNotifyPwa] = useState<"sim" | "nao">("sim");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastCreated, setLastCreated] = useState<
    { id: string; codigo_se: string; hash_evento: string } | null
  >(null);

  // Fechamento via Esc é bloqueado durante submitting (E4).
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        handleClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, submitting]);

  function handleClose() {
    if (submitting) return;
    onClose();
  }

  const tpaOutIdResolved = useMemo(() => {
    if (prefill?.tpa_id) return prefill.tpa_id;
    const mat = tpaOutMatricula.trim();
    if (!mat) return "";
    const cell =
      catalogo.cells.find((c) => c.tpa_matricula === mat) ??
      catalogo.cells.find((c) => c.tpa_id === mat);
    return cell?.tpa_id ?? "";
  }, [prefill?.tpa_id, tpaOutMatricula, catalogo.cells]);

  const tpaInIdResolved = useMemo(() => {
    const mat = tpaInMatricula.trim();
    if (!mat) return "";
    const cell = catalogo.cells.find((c) => c.tpa_matricula === mat);
    return cell?.tpa_id ?? "";
  }, [tpaInMatricula, catalogo.cells]);

  const funcaoLabel =
    catalogo.funcoes.find((f) => f.id === funcaoId)?.nome ?? "—";

  useEffect(() => {
    if (!prefill?.tpa_id) return;
    const cell = catalogo.cells.find((c) => c.tpa_id === prefill.tpa_id);
    if (cell?.tpa_matricula) {
      setTpaOutMatricula(cell.tpa_matricula);
    }
    if (cell?.funcao_id && !funcaoId) setFuncaoId(cell.funcao_id);
    if (cell?.faina_id && !fainaId) setFainaId(cell.faina_id);
    if (cell?.cais && !caisOrigem) setCaisOrigem(cell.cais);
  }, [prefill?.tpa_id, catalogo.cells, funcaoId, fainaId, caisOrigem]);

  function applyMatriculaOutLookup() {
    const mat = tpaOutMatricula.trim();
    if (!mat) return;
    const cell = catalogo.cells.find((c) => c.tpa_matricula === mat);
    if (!cell) return;
    if (cell.funcao_id) setFuncaoId(cell.funcao_id);
    if (cell.faina_id) setFainaId(cell.faina_id);
    if (cell.cais) setCaisOrigem(cell.cais);
  }

  // UX2: além do flag `canSubmit`, devolvemos `camposPendentes` com a lista
  // de rótulos dos campos que ainda bloqueiam o submit. Tudo derivado do
  // mesmo `useMemo` para garantir sincronia entre a regra e a lista
  // exibida (mitiga risco SPEC §5.3). UX silenciosa quando `canSubmit` é
  // `true` (helper text não renderiza e `title` é `undefined`).
  const canSubmit = useMemo<{ canSubmit: boolean; camposPendentes: string[] }>(() => {
    const camposPendentes: string[] = [];
    const valido: boolean = ((): boolean => {
      if (submitting) { camposPendentes.push("envio em andamento"); return false; }
      if (!confirmCct) { camposPendentes.push("ack CCT"); return false; }
      if (!portoId || !turnoId) { camposPendentes.push("porto/turno"); return false; }
      if (!tpaOutIdResolved) {
        camposPendentes.push(
          labelPendenciaTpaOut(tpaOutMatricula, tpaOutIdResolved),
        );
        return false;
      }
      if (!funcaoId || !fainaId) { camposPendentes.push("função e faina"); return false; }
      if (!motivo) { camposPendentes.push("motivo"); return false; }
      if (motivo === "OUTRO" && motivoOutro.trim() === "") { camposPendentes.push("motivo_outro_texto"); return false; }
      if (motivo !== "OUTRO" && motivoOutro !== "" && motivoOutro.length > MAX_MOTIVO_OUTRO) { camposPendentes.push("motivo_outro_texto"); return false; }
      if (baseLegalMode === "catalogo" && !baseLegalCctId) { camposPendentes.push("base legal"); return false; }
      if (baseLegalMode === "livre" && (baseLegalLivre.trim() === "" || baseLegalLivre.length > MAX_BASE_LEGAL_LIVRE)) { camposPendentes.push("base legal"); return false; }
      if (observacoes.length > MAX_OBSERVACOES || caisOrigem.length > 8) { camposPendentes.push("cais de origem/observações"); return false; }
      return true;
    })();
    return { canSubmit: valido, camposPendentes };
  }, [submitting, portoId, turnoId, tpaOutIdResolved, tpaOutMatricula, confirmCct, funcaoId, fainaId, motivo, motivoOutro, baseLegalMode, baseLegalCctId, baseLegalLivre, observacoes, caisOrigem]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit.canSubmit) return;
    setSubmitting(true);
    setSubmitError(null);

    // Payload casa com `RemanejamentoBase` Pydantic — sem `notify_pwa`/`ack_cct`.
    const payload: RemanejamentoCreate = {
      porto_id: portoId,
      turno_id: turnoId,
      data_referencia: dataReferencia,
      tpa_out_id: tpaOutIdResolved,
      funcao_origem_id: funcaoId,
      faina_origem_id: fainaId,
      cais_origem: caisOrigem || null,
      tpa_in_id: tpaInIdResolved || null,
      motivo,
      motivo_outro_texto:
        motivo === "OUTRO"
          ? motivoOutro || null
          : motivoOutro.trim() !== ""
            ? motivoOutro
            : null,
      base_legal_cct_id: baseLegalMode === "catalogo" ? baseLegalCctId : null,
      base_legal_texto_livre:
        baseLegalMode === "livre" ? baseLegalLivre : null,
      observacoes: observacoes.trim() !== "" ? observacoes : null,
      anexo_url: anexoUrl.trim() !== "" ? anexoUrl : null,
    };

    try {
      const created = await createRemanejamento(payload);
      const codigoSe = created.codigo_se ?? "";
      const hashEvento = created.hash_evento ?? "";
      const id = created.id ?? "";

      if (executarENotificarOgmo && id) {
        try {
          await aprovarRemanejamento(id);
          await notifyOgmo(id);
        } catch (notifyErr) {
          const detail =
            notifyErr instanceof ApiError
              ? notifyErr.detail
              : notifyErr instanceof Error
                ? notifyErr.message
                : "Falha ao notificar OGMO";
          setSubmitError(
            `Remanejamento criado (${codigoSe}), mas a notificação ao OGMO falhou: ${detail}`,
          );
          setSubmitting(false);
          onCreated?.({ id, codigo_se: codigoSe, hash_evento: hashEvento });
          return;
        }
      }

      setLastCreated({ id, codigo_se: codigoSe, hash_evento: hashEvento });
      // Mantém modal aberto 1,5s exibindo o sucesso (HU001/CA04), então
      // dispara `onCreated` e fecha. O reset de `submitting` é feito antes
      // do `onClose` para evitar novo submit durante a janela de 1,5s.
      window.setTimeout(() => {
        setSubmitting(false);
        onCreated?.({ id, codigo_se: codigoSe, hash_evento: hashEvento });
        onClose();
      }, SUCCESS_HOLD_MS);
      return;
    } catch (err) {
      // 404 TPA_OUT_NOT_FOUND mantém modal aberto (HU001/CA05).
      if (err instanceof ApiError && err.status === 404) {
        const detail = err.detail || "";
        if (
          detail.includes("TPA_OUT_NOT_FOUND") ||
          /TPA\s+out/i.test(detail)
        ) {
          setSubmitError(MSG_TPA_OUT_NAO_ENCONTRADO);
          setSubmitting(false);
          return;
        }
      }
      const fallback =
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Erro ao criar remanejamento.";
      setSubmitError(fallback);
      setSubmitting(false);
    }
  }

  if (!open) return null;

  // ---- Render --------------------------------------------------------------

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reman-modal-title"
      className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 overflow-y-auto"
      onClick={handleClose}
    >
      <div
        className="w-full max-w-lg rounded-lg border border-[#2a5070] bg-[#0a1929] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {lastCreated ? (
          <div className="p-6">
            <div className="mb-3 flex items-center gap-2">
              <StatusBadge tone="green">✓ Criado</StatusBadge>
            </div>
            <h2 id="reman-modal-title" className="mb-2 text-lg font-bold text-[#e8eef4]">
              Remanejamento registrado
            </h2>
            <p className="mb-4 text-[12px] text-[#94a8bd]">
              Código SE:{" "}
              <span className="font-mono text-[#d4a574]">{lastCreated.codigo_se}</span>{" "}
              · Hash:{" "}
              <span className="font-mono text-[#d4a574]">{lastCreated.hash_evento}</span>
            </p>
            <p className="text-[12px] text-[#94a8bd]">
              Aguarde — fechando em instantes…
            </p>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2
                id="reman-modal-title"
                className="text-lg font-bold text-[#e8eef4]"
              >
                Remanejamento de TPA
              </h2>
              <button
                type="button"
                onClick={handleClose}
                disabled={submitting}
                className="text-[#94a8bd] hover:text-[#e8eef4]"
                aria-label="Fechar"
              >
                ✕
              </button>
            </div>

            <div className="remanejamento-contexto mb-4 text-[12px] text-[#94a8bd]">
              Contexto:{" "}
              <strong className="text-[#e8eef4]">
                Cais {caisOrigem || "—"} · Turno {turno} · Função {funcaoLabel}
              </strong>
            </div>

            <Field label="TPA a remover (matrícula)">
              <input
                type="text"
                value={tpaOutMatricula}
                onChange={(e) => setTpaOutMatricula(e.target.value)}
                onBlur={applyMatriculaOutLookup}
                placeholder="Ex.: 012"
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              />
              {tpaOutMatricula.trim() !== "" && !tpaOutIdResolved && (
                <p className="mt-1 text-[11px] text-[#e04a4a]">
                  Matrícula sem cadastro no Sindicato — solicite backfill ou cadastro
                  do TPA antes de remanejar.
                </p>
              )}
            </Field>

            <Field label="TPA a inserir (opcional)">
              <input
                type="text"
                value={tpaInMatricula}
                onChange={(e) => setTpaInMatricula(e.target.value)}
                placeholder="Ex.: 245 ou vazio (OGMO decide)"
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              />
            </Field>

            {/* Função / Faina — selects com códigos do catálogo
                (modo "sem prefill" quando F3 não recebe query params). */}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Função">
                <select
                  value={funcaoId}
                  onChange={(e) => setFuncaoId(e.target.value)}
                  className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
                >
                  <option value="">— Selecionar —</option>
                  {catalogo.funcoes.map((fn) => (
                    <option key={fn.id} value={fn.id}>
                      {fn.codigo} · {fn.nome}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Faina">
                <select
                  value={fainaId}
                  onChange={(e) => setFainaId(e.target.value)}
                  className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
                >
                  <option value="">— Selecionar —</option>
                  {catalogo.fainas.map((fn) => (
                    <option key={fn.id} value={fn.id}>
                      {fn.codigo} · {fn.nome}
                    </option>
                  ))}
                </select>
              </Field>
            </div>

            <Field label="Motivo do remanejamento">
              <select
                value={motivo}
                onChange={(e) => setMotivo(e.target.value as MotivoRemanejamentoUi)}
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              >
                {motivos.map((m) => (
                  <option key={m} value={m}>
                    {labelForMotivo(m)}
                  </option>
                ))}
              </select>
            </Field>

            {/* motivo_outro_texto (≤ 1000) com contador */}
            <Field label="Detalhe do motivo (opcional, ≤ 1000)">
              <textarea
                value={motivoOutro}
                onChange={(e) => setMotivoOutro(e.target.value.slice(0, MAX_MOTIVO_OUTRO))}
                rows={2}
                maxLength={MAX_MOTIVO_OUTRO}
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
                placeholder="Detalhe adicional do motivo (somente quando relevante)."
              />
              <Counter value={motivoOutro.length} max={MAX_MOTIVO_OUTRO} />
            </Field>

            {/* Cais origem (E5 — maxLength 8) */}
            <Field label="Cais de origem (≤ 8)">
              <input
                type="text"
                value={caisOrigem}
                onChange={(e) => setCaisOrigem(e.target.value.slice(0, 8))}
                maxLength={8}
                placeholder="Ex.: CAIS 2"
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              />
            </Field>

            {/* Data referência (E2 — min/max hoje-7d a hoje) */}
            <Field label="Data de referência">
              <input
                type="date"
                value={dataReferencia}
                min={minData}
                max={maxData}
                onChange={(e) => setDataReferencia(e.target.value)}
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              />
            </Field>

            {/* Base legal — select CCT + textarea mutuamente exclusivos (E3) */}
            <Field label="Base legal / CCT">
              {baseLegalMode === "catalogo" ? (
                <>
                  <select
                    value={baseLegalCctId}
                    onChange={(e) => setBaseLegalCctId(e.target.value)}
                    className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
                  >
                    <option value="">— Selecionar cláusula —</option>
                    {basesLegais.map((b) => (
                      <option key={b.id} value={b.id}>
                        CCT {b.versao_cct} · {b.clausula}
                      </option>
                    ))}
                  </select>
                  {basesLegais.length === 0 ? null : (
                    <button
                      type="button"
                      onClick={() => setBaseLegalMode("livre")}
                      className="mt-1 text-[10px] text-[#94a8bd] underline-offset-2 hover:text-[#e8eef4] hover:underline"
                    >
                      Não achei no catálogo
                    </button>
                  )}
                </>
              ) : (
                <>
                  <textarea
                    value={baseLegalLivre}
                    onChange={(e) =>
                      setBaseLegalLivre(e.target.value.slice(0, MAX_BASE_LEGAL_LIVRE))
                    }
                    maxLength={MAX_BASE_LEGAL_LIVRE}
                    rows={3}
                    placeholder="Descreva a base legal em texto livre (≤ 500)."
                    className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
                  />
                  <div className="flex items-center justify-between">
                    <Counter value={baseLegalLivre.length} max={MAX_BASE_LEGAL_LIVRE} />
                    <button
                      type="button"
                      onClick={() => setBaseLegalMode("catalogo")}
                      className="text-[10px] text-[#94a8bd] underline-offset-2 hover:text-[#e8eef4] hover:underline"
                    >
                      Usar catálogo de CCT
                    </button>
                  </div>
                </>
              )}
            </Field>

            {/* Observações (≤ 2000) com contador */}
            <Field label="Observações">
              <textarea
                value={observacoes}
                onChange={(e) =>
                  setObservacoes(e.target.value.slice(0, MAX_OBSERVACOES))
                }
                maxLength={MAX_OBSERVACOES}
                rows={3}
                placeholder="Detalhes que ajudem o OGMO a processar..."
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              />
              <Counter value={observacoes.length} max={MAX_OBSERVACOES} />
            </Field>

            <Field label="Anexar documento (opcional)">
              <input
                type="file"
                disabled
                title="Upload de arquivo em breve — use URL abaixo se necessário."
                className="w-full text-[12px] text-[#94a8bd]"
              />
              <input
                type="url"
                value={anexoUrl}
                onChange={(e) => setAnexoUrl(e.target.value)}
                placeholder="URL do anexo (opcional)"
                className="mt-2 w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              />
            </Field>

            <Field label="Notificar TPA via PWA">
              <select
                value={notifyPwa}
                onChange={(e) =>
                  setNotifyPwa(e.target.value === "nao" ? "nao" : "sim")
                }
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              >
                <option value="sim">Sim, push imediato</option>
                <option value="nao">Não notificar agora</option>
              </select>
            </Field>

            <label className="mb-4 flex cursor-pointer items-start gap-2 text-[12px] text-[#e8eef4]">
              <input
                type="checkbox"
                checked={confirmCct}
                onChange={(e) => setConfirmCct(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                Confirmo que este remanejamento é lícito e respaldado pela CCT
                vigente
              </span>
            </label>

            {/* Erro inline (HU001/CA05) */}
            {submitError && (
              <div
                role="alert"
                className="mb-3 rounded border border-[#e04a4a]/40 bg-[#e04a4a]/10 px-3 py-2 text-[12px] text-[#e04a4a]"
              >
                {submitError}
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleClose}
                disabled={submitting}
                className="rounded border border-[#2a5070] px-4 py-2 text-[12px] font-semibold text-[#94a8bd] hover:text-[#e8eef4] disabled:opacity-50"
              >
                Cancelar
              </button>

              {/* UX2 — feedback "o que falta" (SPEC §4.2 UX2): helper text
                  `<p>Pendente: ...</p>` + tooltip acessível via `title` no
                  botão submit abaixo. Só aparecem quando
                  canSubmit.canSubmit === false (UX silenciosa no sucesso).
                  Lista derivada do mesmo useMemo da regra de canSubmit
                  (SPEC §5.3: mitigação de drift). */}

              {!canSubmit.canSubmit && (
                <p className="text-[10px] text-[#94a8bd] mt-1">
                  Pendente: {canSubmit.camposPendentes.join(", ")}
                </p>
              )}

              <button
                type="submit"
                disabled={!canSubmit.canSubmit}
                title={canSubmit.canSubmit ? undefined : canSubmit.camposPendentes.join(", ")}
                className="rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a] disabled:opacity-50"
              >
                {submitting
                  ? "Enviando…"
                  : executarENotificarOgmo
                    ? "Executar e notificar OGMO"
                    : "Criar Remanejamento"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}): ReactNode {
  return (
    <div className="mb-3">
      <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-[#94a8bd]">
        {label}
      </label>
      {children}
    </div>
  );
}

function Counter({ value, max }: { value: number; max: number }): ReactNode {
  const over = value > max;
  return (
    <div
      className={`mt-1 text-right text-[10px] ${over ? "text-[#e04a4a]" : "text-[#94a8bd]"}`}
    >
      {value}/{max}
    </div>
  );
}