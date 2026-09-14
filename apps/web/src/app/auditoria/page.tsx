// =============================================================================
// SINDESTIVA-PE · /auditoria — Eventos + verificador de hash chain (HU006).
//
// Mudanças vs Sprint 7 (mock):
//   - Default `getAuditEvents(100)` (era 50).
//   - Filtro `entity_type` via `<select>` cobre os 5 valores que o
//     backend emite hoje (REMANEJAMENTO / AUTH / OGMO_NOTIFICACAO /
//     SCRAPING / AUDIT_EVENT). "Todos" = sem filtro.
//   - Botão "Carregar mais" incrementa o limit em +100 e re-busca.
//   - Campo `actor` renderizado exatamente como o mapper entrega
//     (`<actor_nome> · <actor_role>` com U+00B7, fallback
//     `usuário <8>…` quando ausente — ver `formatActor` em
//     `apps/web/src/lib/api-mappers.ts`).
//   - Botão "🔍 Verificar hash chain agora" + banner integro/quebrado
//     mantidos sem mudança.
//
// =============================================================================

"use client";

import { useEffect, useState, type ReactNode } from "react";
import { getAuditEvents, verifyHashChain, ApiError } from "@/lib/api";
import type { AuditEvent } from "@/lib/tipos";
import { StatusBadge } from "@/app/_components/StatusBadge";
import { EmptyState } from "@/app/_components/EmptyState";
import { shortHashPrefix } from "@/lib/api-mappers";

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

/** Opções do filtro de entity_type. "TODOS" = sem filtro (string vazia no fetch). */
const ENTITY_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "",                  label: "Todos" },
  { value: "REMANEJAMENTO",     label: "Remanejamento" },
  { value: "AUTH",              label: "Auth" },
  { value: "OGMO_NOTIFICACAO",  label: "OGMO Notificação" },
  { value: "SCRAPING",          label: "Scraping" },
  { value: "AUDIT_EVENT",       label: "Audit Event" },
];

/** Incremento do "Carregar mais" — uma página adicional por clique. */
const PAGE_STEP = 100;

export default function AuditoriaPage(): ReactNode {
  const [items, setItems] = useState<AuditEvent[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [verify, setVerify] = useState<{
    integro: boolean;
    total_eventos: number;
    primeiro_evento_com_falha: number | null;
    duracao_ms: number;
  } | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [entityType, setEntityType] = useState<string>("");
  const [limit, setLimit] = useState<number>(100);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    setLoadError(null);
    setItems(null);
    getAuditEvents(100, entityType || undefined)
      .then(setItems)
      .catch((err) => {
        const msg =
          err instanceof ApiError ? err.detail : err instanceof Error ? err.message : "Erro";
        setLoadError(msg);
        setItems([]);
      });
  }, [entityType]);

  async function onLoadMore(): Promise<void> {
    setLoadingMore(true);
    try {
      const next = limit + PAGE_STEP;
      const more = await getAuditEvents(next, entityType || undefined);
      setItems(more);
      setLimit(next);
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.detail : err instanceof Error ? err.message : "Erro";
      setLoadError(msg);
    } finally {
      setLoadingMore(false);
    }
  }

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
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-[#94a8bd]">
            entity_type
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="rounded border border-[#2a5070] bg-[#0f2438] px-2 py-1 text-[12px] text-[#e8eef4]"
            >
              {ENTITY_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value || "TODOS"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={onVerify}
            disabled={verifying}
            className="rounded border border-[#d4a574] px-4 py-2 text-[12px] font-bold uppercase tracking-wide text-[#d4a574] hover:bg-[#d4a574]/10 disabled:opacity-50"
          >
            {verifying ? "Verificando…" : "🔍 Verificar hash chain agora"}
          </button>
        </div>
      </div>

      {verify && (
        <div
          className={`mb-4 rounded-md border p-3 text-[12px] ${
            verify.integro
              ? "border-[#5dbb7d]/40 bg-[#5dbb7d]/10 text-[#5dbb7d]"
              : "border-[#e04a4a]/40 bg-[#e04a4a]/10 text-[#e04a4a]"
          }`}
        >
          {verify.integro ? (
            <>
              ✓ <strong>Integridade OK</strong> · {verify.total_eventos} eventos verificados ·
              {verify.duracao_ms} ms · nenhum elo quebrado
            </>
          ) : (
            <>
              ❌ <strong>Quebra detectada</strong> · primeiro evento quebrado em #
              {verify.primeiro_evento_com_falha} de {verify.total_eventos}
            </>
          )}
        </div>
      )}

      {loadError && (
        <div className="login-error mb-4" role="alert">
          ⚠ {loadError}
        </div>
      )}

      {items === null ? (
        <div className="loading">Carregando eventos…</div>
      ) : items.length === 0 && !loadError ? (
        <EmptyState
          icon="🔗"
          title="Nenhum evento de auditoria ainda"
          description="Logins, scrapes e remanejamentos passam a gerar eventos append-only na hash chain assim que a operação começar."
        />
      ) : items.length === 0 ? null : (
        <>
          <div className="rounded-lg border border-[#1e3a52] bg-[#0f2438]">
            <ol className="divide-y divide-[#1e3a52]">
              {items.map((e) => {
                const meta = KIND_LABEL[e.kind] ?? { label: e.kind, tone: "muted" as const };
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
                            <span className="font-mono text-[#d4a574]">
                              {shortHashPrefix(e.hash_evento)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#94a8bd]">hash_anterior:</span>{" "}
                            <span className="font-mono text-[#d4a574]">
                              {shortHashPrefix(e.hash_anterior)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <span className="text-[11px] text-[#94a8bd]">
              Exibindo {items.length} evento(s){entityType ? ` · filtro: ${entityType}` : ""}
            </span>
            <button
              type="button"
              onClick={() => void onLoadMore()}
              disabled={loadingMore}
              className="rounded border border-[#2a5070] bg-[#0f2438] px-4 py-2 text-[12px] font-semibold uppercase tracking-wide text-[#e8eef4] hover:bg-[#1a2540] disabled:opacity-50"
            >
              {loadingMore ? "Carregando…" : "Carregar mais"}
            </button>
          </div>
        </>
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
