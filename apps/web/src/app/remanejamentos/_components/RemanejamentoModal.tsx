// =============================================================================
// SINDESTIVA-PE · RemanejamentoModal — modal pré-preenchido para novo remanejamento
// Pode receber contexto via query params (vindo do clique no ponteiro da lousa).
// Sprint 5 (T5-02) implementa de verdade: TPA a inserir, motivo, base legal,
// observações, anexo, notify PWA, checkbox ack CCT.
// =============================================================================

"use client";

import { useState, type ReactNode, type FormEvent } from "react";
import type { Porto, Turno } from "@sindestiva/shared";
import { StatusBadge, toneForOgmoStatus } from "@/app/_components/StatusBadge";
import type { RemanejamentoCreate, RemanejamentoItem } from "@/lib/tipos";
import { createRemanejamento } from "@/lib/api";

const MOTIVOS = [
  "Atestado médico",
  "Falta justificada",
  "Reforço de terno (navio extra)",
  "Substituição rotina",
  "Trocou p/ outro turno",
  "Liberação sindical",
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
  /** Callback quando o remanejamento for criado (mock). */
  onCreated?: (item: RemanejamentoItem) => void;
  /** Callback para fechar. */
  onClose: () => void;
  porto: Porto;
  turno: Turno;
}

export function RemanejamentoModal({ prefill, onCreated, onClose, porto, turno }: RemanejamentoModalProps): ReactNode {
  const [motivo, setMotivo] = useState<string>(MOTIVOS[0] ?? "");
  const [baseLegal, setBaseLegal] = useState<string>(BASES_LEGAIS[0] ?? "");
  const [tpaSubstituto, setTpaSubstituto] = useState<string>("");
  const [observacoes, setObservacoes] = useState<string>("");
  const [notifyPwa, setNotifyPwa] = useState<boolean>(true);
  const [ackCct, setAckCct] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [lastCreated, setLastCreated] = useState<RemanejamentoItem | null>(null);

  const canSubmit = ackCct && motivo !== "" && baseLegal !== "" && !submitting;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    const payload: RemanejamentoCreate = {
      tpa_removido_id: prefill?.tpa_id ?? "tpa-unknown",
      funcao_codigo: prefill?.funcao_codigo ?? "CM_GERAL",
      faina_codigo: prefill?.faina_codigo ?? "PRODUCAO",
      motivo,
      base_legal: baseLegal,
      observacoes: observacoes || undefined,
      notify_pwa: notifyPwa,
      ack_cct: ackCct,
    };
    try {
      const created = await createRemanejamento(payload);
      setLastCreated(created);
      onCreated?.(created);
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
          // Estado de sucesso (mock — Sprint 5 retorna do backend)
          <div className="p-6">
            <div className="mb-3 flex items-center gap-2">
              <StatusBadge tone="green">✓ Criado</StatusBadge>
              <StatusBadge tone={toneForOgmoStatus(lastCreated.status)}>
                {lastCreated.status}
              </StatusBadge>
            </div>
            <h2 id="reman-modal-title" className="mb-2 text-lg font-bold text-[#e8eef4]">
              Remanejamento registrado
            </h2>
            <p className="mb-4 text-[12px] text-[#94a8bd]">
              ID: <span className="font-mono text-[#d4a574]">{lastCreated.id}</span> ·
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
                onChange={(e) => setMotivo(e.target.value)}
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

            <div className="mb-4 space-y-2">
              <label className="flex cursor-pointer items-center gap-2 text-[12px] text-[#e8eef4]">
                <input
                  type="checkbox"
                  checked={notifyPwa}
                  onChange={(e) => setNotifyPwa(e.target.checked)}
                  className="h-4 w-4 accent-[#d4a574]"
                />
                Notificar PWA do TPA
              </label>
              <label className="flex cursor-pointer items-start gap-2 text-[12px] text-[#e8eef4]">
                <input
                  type="checkbox"
                  checked={ackCct}
                  onChange={(e) => setAckCct(e.target.checked)}
                  className="mt-0.5 h-4 w-4 accent-[#d4a574]"
                />
                <span>
                  Confirmo que este remanejamento respeita a <strong>CCT 2024-2026</strong> e a
                  base legal indicada acima. <span className="text-[#e04a4a]">Obrigatório.</span>
                </span>
              </label>
            </div>

            {!ackCct && (
              <div className="mb-3 rounded border border-[#e04a4a]/40 bg-[#e04a4a]/10 px-3 py-2 text-[11px] text-[#e04a4a]">
                ⚠️ Confirme o ack CCT para habilitar o envio.
              </div>
            )}

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
