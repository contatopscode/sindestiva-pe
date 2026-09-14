// =============================================================================
// SINDESTIVA-PE · RemanejamentoModal — modal pré-preenchido para novo remanejamento
// Pode receber contexto via query params (vindo do clique no ponteiro da lousa).
// Sprint S2: payload alinhado com `RemanejamentoBase` (Pydantic) — sem
// `notify_pwa`/`ack_cct`. Migração completa da UX (selects por enum, base
// legal CCT por catálogo, limites de texto, etc.) acontece em sprints
// futuras — este sprint só garante o contrato de payload/tipo.
// =============================================================================

"use client";

import { useState, type ReactNode, type FormEvent } from "react";
import type { Porto, Turno } from "@sindestiva/shared";
import { StatusBadge, toneForStatusRemanejamento } from "@/app/_components/StatusBadge";
import type { MotivoRemanejamentoUi, RemanejamentoCreate } from "@/lib/tipos";
import type { RemanejamentoItemResolved } from "@/lib/api-mappers";
import { createRemanejamento } from "@/lib/api";

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

const BASES_LEGAIS = [
  "CCT 2024-2026 · Cláusula 7ª, §1º",
  "CCT 2024-2026 · Cláusula 7ª, §2º",
  "CCT 2024-2026 · Cláusula 7ª, §3º",
  "CCT 2024-2026 · Cláusula 5ª (troca de turno)",
];

export interface RemanejamentoModalProps {
  /** Contexto vindo do clique no ponteiro (opcional). */
  prefill?: {
    tpa_id?: string;
    faina_codigo?: string;
    funcao_codigo?: string;
  };
  /** Callback quando o remanejamento for criado. */
  onCreated?: (item: RemanejamentoItemResolved) => void;
  /** Callback para fechar. */
  onClose: () => void;
  porto: Porto;
  turno: Turno;
}

export function RemanejamentoModal({ prefill, onCreated, onClose, porto, turno }: RemanejamentoModalProps): ReactNode {
  const [motivo, setMotivo] = useState<MotivoRemanejamentoUi>(MOTIVOS[0] ?? "OUTRO");
  const [baseLegal, setBaseLegal] = useState<string>(BASES_LEGAIS[0] ?? "");
  const [tpaSubstituto, setTpaSubstituto] = useState<string>("");
  const [observacoes, setObservacoes] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [lastCreated, setLastCreated] = useState<RemanejamentoItemResolved | null>(null);

  const canSubmit = baseLegal !== "" && !submitting;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    // Payload espelha `RemanejamentoBase` (Pydantic). Sem `notify_pwa`/`ack_cct`.
    const payload: RemanejamentoCreate = {
      porto_id: prefill?.tpa_id ?? "00000000-0000-0000-0000-000000000000",
      turno_id: "00000000-0000-0000-0000-000000000000",
      data_referencia: new Date().toISOString().slice(0, 10),
      tpa_out_id: prefill?.tpa_id ?? "00000000-0000-0000-0000-000000000000",
      funcao_origem_id: "00000000-0000-0000-0000-000000000000",
      faina_origem_id: "00000000-0000-0000-0000-000000000000",
      motivo,
      base_legal_texto_livre: baseLegal,
      observacoes: observacoes || undefined,
    };
    try {
      const created = await createRemanejamento(payload);
      // O backend devolve um item cru — o mapper só é aplicado em
      // listagens, aqui só exibimos o essencial.
      const resolved: RemanejamentoItemResolved = {
        ...(created as unknown as RemanejamentoItemResolved),
        tpa_removido_nome: "(nome removido)",
        tpa_removido_matricula: "—",
        funcao_origem_nome: "(função removida)",
        funcao_origem_codigo: "—",
        faina_origem_nome: "(faina removida)",
        faina_origem_codigo: "—",
        base_legal_texto: baseLegal,
      };
      if (tpaSubstituto) {
        resolved.tpa_substituto_nome = tpaSubstituto;
      }
      setLastCreated(resolved);
      onCreated?.(resolved);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reman-modal-title"
      className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-lg border border-[#2a5070] bg-[#0a1929] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {lastCreated ? (
          <div className="p-6">
            <div className="mb-3 flex items-center gap-2">
              <StatusBadge tone="green">✓ Criado</StatusBadge>
              <StatusBadge tone={toneForStatusRemanejamento(lastCreated.status)}>
                {lastCreated.status}
              </StatusBadge>
            </div>
            <h2 id="reman-modal-title" className="mb-2 text-lg font-bold text-[#e8eef4]">
              Remanejamento registrado
            </h2>
            <p className="mb-4 text-[12px] text-[#94a8bd]">
              Código SE: <span className="font-mono text-[#d4a574]">{lastCreated.codigo_se}</span> ·
              Hash: <span className="font-mono text-[#d4a574]">{lastCreated.hash_evento}</span>
            </p>
            <p className="mb-4 text-[12px] text-[#94a8bd]">
              Em produção, o e-mail será enviado ao OGMO e o PWA do TPA será notificado.
            </p>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a]"
              >
                OK
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 id="reman-modal-title" className="text-lg font-bold text-[#e8eef4]">
                Novo Remanejamento
              </h2>
              <div className="flex items-center gap-2 text-[11px] text-[#94a8bd]">
                <span className="rounded bg-[#1e3a52] px-2 py-0.5 font-mono">{porto}</span>
                <span className="rounded bg-[#1e3a52] px-2 py-0.5 font-mono">{turno}</span>
              </div>
            </div>

            {/* Contexto pré-preenchido */}
            <div className="mb-4 rounded-md border border-[#1e3a52] bg-[#0f2438] p-3 text-[12px]">
              <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-[#94a8bd]">
                Contexto (pré-preenchido)
              </div>
              <dl className="grid grid-cols-[110px_1fr] gap-y-1 text-[#e8eef4]">
                <dt className="text-[#94a8bd]">TPA removido</dt>
                <dd className="font-mono">{prefill?.tpa_id ?? "—"}</dd>
                <dt className="text-[#94a8bd]">Função</dt>
                <dd>{prefill?.funcao_codigo ?? "—"}</dd>
                <dt className="text-[#94a8bd]">Faina</dt>
                <dd>{prefill?.faina_codigo ?? "—"}</dd>
              </dl>
            </div>

            <Field label="TPA substituto (opcional)">
              <input
                type="text"
                value={tpaSubstituto}
                onChange={(e) => setTpaSubstituto(e.target.value)}
                placeholder="Matrícula OGMO ou nome"
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              />
            </Field>

            <Field label="Motivo">
              <select
                value={motivo}
                onChange={(e) => setMotivo(e.target.value as MotivoRemanejamentoUi)}
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              >
                {MOTIVOS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </Field>

            <Field label="Base legal">
              <select
                value={baseLegal}
                onChange={(e) => setBaseLegal(e.target.value)}
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              >
                {BASES_LEGAIS.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </Field>

            <Field label="Observações (opcional)">
              <textarea
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                rows={2}
                className="w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
              />
            </Field>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded border border-[#2a5070] px-4 py-2 text-[12px] font-semibold text-[#94a8bd] hover:text-[#e8eef4]"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                className="rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a] disabled:opacity-50"
              >
                {submitting ? "Enviando…" : "Criar Remanejamento"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mb-3">
      <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-[#94a8bd]">
        {label}
      </label>
      {children}
    </div>
  );
}
