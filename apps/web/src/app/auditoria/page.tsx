// =============================================================================
// SINDESTIVA-PE · /auditoria — Eventos + verificador de hash chain
// Mock até Sprint 6 (T6) implementar o verificador real com SHA-256.
// =============================================================================

"use client";

import { useEffect, useState, type ReactNode } from "react";
import { getAuditEvents, verifyHashChain } from "@/lib/api";
import type { AuditEvent } from "@/lib/tipos";
import { StatusBadge } from "@/app/_components/StatusBadge";

const KIND_LABEL: Record<AuditEvent["kind"], { label: string; tone: "green" | "amber" | "red" | "cyan" | "purple" | "gold" | "muted" }> = {
  SCRAPING_OK:         { label: "Scraping OK",   tone: "green" },
  SCRAPING_ERRO:       { label: "Scraping Erro", tone: "red" },
  SCRAPING_PARCIAL:    { label: "Scraping Parcial", tone: "amber" },
  LAYOUT_MUDOU:        { label: "Layout mudou",  tone: "purple" },
  REMANEJAMENTO_CRIADO:{ label: "Remanej. criado", tone: "cyan" },
  REMANEJAMENTO_ENVIADO:{ label: "Remanej. enviado", tone: "cyan" },
  OGMO_ACK:            { label: "OGMO ACK",      tone: "green" },
  OGMO_NACK:           { label: "OGMO NACK",     tone: "red" },
  LOGIN:               { label: "Login",         tone: "muted" },
  LOGOUT:              { label: "Logout",        tone: "muted" },
};

export default function AuditoriaPage(): ReactNode {
  const [items, setItems] = useState<AuditEvent[] | null>(null);
  const [verify, setVerify] = useState<{ ok: boolean; verificados: number; quebrados: number } | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    getAuditEvents(50).then(setItems);
  }, []);

  async function onVerify() {
    setVerifying(true);
    try {
      const r = await verifyHashChain();
      setVerify(r);
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Auditoria &amp; Integridade</h1>
          <p className="section-subtitle">
            Timeline de eventos do sistema · hash chain SHA-256
          </p>
        </div>
        <button
          type="button"
          onClick={onVerify}
          disabled={verifying}
          className="rounded border border-[#d4a574] px-4 py-2 text-[12px] font-bold uppercase tracking-wide text-[#d4a574] hover:bg-[#d4a574]/10 disabled:opacity-50"
        >
          {verifying ? "Verificando…" : "🔍 Verificar hash chain agora"}
        </button>
      </div>

      {verify && (
        <div
          className={`mb-4 rounded-md border p-3 text-[12px] ${
            verify.ok && verify.quebrados === 0
              ? "border-[#5dbb7d]/40 bg-[#5dbb7d]/10 text-[#5dbb7d]"
              : "border-[#e04a4a]/40 bg-[#e04a4a]/10 text-[#e04a4a]"
          }`}
        >
          {verify.ok && verify.quebrados === 0 ? (
            <>
              ✓ <strong>Integridade OK</strong> · {verify.verificados} eventos verificados ·
              nenhum elo quebrado
            </>
          ) : (
            <>
              ❌ <strong>Quebra detectada</strong> · {verify.quebrados} elos comprometidos de{" "}
              {verify.verificados}
            </>
          )}
        </div>
      )}

      {items === null ? (
        <div className="loading">Carregando eventos…</div>
      ) : (
        <div className="rounded-lg border border-[#1e3a52] bg-[#0f2438]">
          <ol className="divide-y divide-[#1e3a52]">
            {items.map((e) => {
              const meta = KIND_LABEL[e.kind];
              return (
                <li key={e.id} className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <StatusBadge tone={meta.tone}>{meta.label}</StatusBadge>
                        <span className="text-[10px] font-mono text-[#94a8bd]">
                          {new Date(e.created_at).toLocaleString("pt-BR")}
                        </span>
                        <span className="text-[10px] text-[#94a8bd]">·</span>
                        <span className="text-[11px] text-[#94a8bd]">{e.actor}</span>
                      </div>
                      <p className="text-[12px] text-[#e8eef4]">{e.descricao}</p>
                      <div className="mt-2 grid grid-cols-1 gap-1 text-[10px] text-[#5f7a92] md:grid-cols-2">
                        <div>
                          <span className="text-[#94a8bd]">hash_evento:</span>{" "}
                          <span className="font-mono text-[#d4a574]">{e.hash_evento.slice(0, 16)}…</span>
                        </div>
                        <div>
                          <span className="text-[#94a8bd]">hash_anterior:</span>{" "}
                          <span className="font-mono text-[#d4a574]">{e.hash_anterior.slice(0, 16)}…</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}

      <div className="mt-4 rounded-md border border-[#1e3a52] bg-[#0a1929] p-3 text-[11px] text-[#94a8bd]">
        <strong>Sobre a hash chain:</strong> cada evento referencia o SHA-256 do
        anterior, criando uma corrente imutável. O verificador recalcula a
        corrente a partir do último snapshot e compara com o que está no banco.
        Implementação completa em Sprint 6 (T6-03 + T6-04).
      </div>
    </div>
  );
}
