// =============================================================================
// SINDESTIVA-PE · RemanejamentosTable
// Sprint S4 — UX completa da HU002: dados reais via catálogo, busca,
// filtro de status, ordenação, paginação (limit=50) e ação "Notificar
// OGMO" (status APROVADO) com debounce 5s e optimistic update.
//
// Resolução de UUIDs (F2 critério): `tpa_out_id`/`tpa_in_id` via
// `cells.find(c => c.tpa_id === ...)`. Idem `funcao_origem_id`/
// `faina_origem_id`. Quando nada bate, renderiza `(nome removido)` em
// vez de `—` (L06-Front).
//
// Quando `status === 'NOTIFICADO_OGMO'`, mantém valor cru no badge com
// tom cyan (decisão D09 da SPEC).
// =============================================================================

"use client";

import {
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import Link from "next/link";
import {
  StatusBadge,
  toneForStatusRemanejamento,
} from "@/app/_components/StatusBadge";
import type {
  Faina,
  Funcao,
  LousaCellOut,
  StatusRemanejamentoUi,
} from "@/lib/tipos";
import type { RemanejamentoItemResolved } from "@/lib/api-mappers";

/** Limite padrão de itens por página (E8/E20 da SPEC). */
const PAGE_LIMIT = 50;
/** Debounce do botão "Notificar OGMO" em ms (D22/E11). */
const NOTIFY_DEBOUNCE_MS = 5_000;

/** 6 status do enum + "TODOS" como sentinel do filtro (E12). */
const STATUSES: Array<StatusRemanejamentoUi | "TODOS"> = [
  "TODOS",
  "PENDENTE",
  "APROVADO",
  "NOTIFICADO_OGMO",
  "ACK",
  "NACK",
  "CANCELADO",
];

export interface RemanejamentosTableCatalogo {
  cells: LousaCellOut[];
  fainas: Faina[];
  funcoes: Funcao[];
}

export interface RemanejamentosTableProps {
  items: RemanejamentoItemResolved[];
  catalogo: RemanejamentosTableCatalogo;
  onNotify: (id: string) => void | Promise<void>;
}

/** Item da tabela após resolução via catálogo (memoizada). */
interface ResolvedRow {
  item: RemanejamentoItemResolved;
  tpaOut: { nome: string; matricula: string } | null;
  tpaIn: { nome: string; matricula: string } | null;
  faina: { nome: string; codigo: string } | null;
  funcao: { nome: string; codigo: string } | null;
}

export function RemanejamentosTable({
  items,
  catalogo,
  onNotify,
}: RemanejamentosTableProps): ReactNode {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<
    StatusRemanejamentoUi | "TODOS"
  >("TODOS");
  const [skip, setSkip] = useState(0);
  /** IDs com ação em curso — usado para desabilitar botão e aplicar debounce. */
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set());

  // ---- Resolução memoizada de IDs via catálogo ----------------------------
  const resolved = useMemo<ResolvedRow[]>(() => {
    const { cells, fainas, funcoes } = catalogo;
    return items.map((item) => {
      const cellOut = cells.find((c) => c.tpa_id === item.tpa_out_id) ?? null;
      const cellIn = item.tpa_in_id
        ? (cells.find((c) => c.tpa_id === item.tpa_in_id) ?? null)
        : null;
      const funcao = funcoes.find((f) => f.id === item.funcao_origem_id) ?? null;
      const faina = fainas.find((f) => f.id === item.faina_origem_id) ?? null;
      return {
        item,
        tpaOut: cellOut
          ? {
              nome: cellOut.tpa_nome ?? "(nome removido)",
              matricula: cellOut.tpa_matricula ?? "—",
            }
          : null,
        tpaIn: cellIn
          ? {
              nome: cellIn.tpa_nome ?? "(nome removido)",
              matricula: cellIn.tpa_matricula ?? "—",
            }
          : null,
        faina: faina ? { nome: faina.nome, codigo: faina.codigo } : null,
        funcao: funcao ? { nome: funcao.nome, codigo: funcao.codigo } : null,
      };
    });
  }, [items, catalogo]);

  // ---- Ordenação + filtro + busca (tudo client-side) ----------------------
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const out = resolved.filter((row) => {
      if (statusFilter !== "TODOS" && row.item.status !== statusFilter) {
        return false;
      }
      if (q.length > 0) {
        const tpaNome = (row.tpaOut?.nome ?? "").toLowerCase();
        const matricula = (row.tpaOut?.matricula ?? "").toLowerCase();
        const motivo = row.item.motivo.toLowerCase();
        const codigoSe = row.item.codigo_se.toLowerCase();
        if (
          !tpaNome.includes(q) &&
          !matricula.includes(q) &&
          !motivo.includes(q) &&
          !codigoSe.includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
    // Ordenação default: created_at desc (E10).
    out.sort((a, b) => {
      const av = Date.parse(a.item.created_at);
      const bv = Date.parse(b.item.created_at);
      return bv - av;
    });
    return out;
  }, [resolved, search, statusFilter]);

  // ---- Paginação (Anterior/Próximo, limit=50) -----------------------------
  const total = filtered.length;
  const pageStart = skip;
  const pageEnd = Math.min(skip + PAGE_LIMIT, total);
  const pageItems = useMemo(
    () => filtered.slice(pageStart, pageEnd),
    [filtered, pageStart, pageEnd],
  );

  function goPrev() {
    setSkip((s) => Math.max(0, s - PAGE_LIMIT));
  }
  function goNext() {
    setSkip((s) => (s + PAGE_LIMIT < total ? s + PAGE_LIMIT : s));
  }

  // ---- Ação "Notificar OGMO" (HU002) --------------------------------------
  const handleNotify = useCallback(
    async (id: string) => {
      if (busyIds.has(id)) return;
      setBusyIds((prev) => {
        const next = new Set(prev);
        next.add(id);
        return next;
      });
      try {
        await onNotify(id);
      } finally {
        // Debounce 5s (D22/E11): mantém busy durante esse intervalo
        // mesmo se `onNotify` resolver instantaneamente.
        setTimeout(() => {
          setBusyIds((prev) => {
            const next = new Set(prev);
            next.delete(id);
            return next;
          });
        }, NOTIFY_DEBOUNCE_MS);
      }
    },
    [busyIds, onNotify],
  );

  return (
    <div className="rounded-lg border border-[#1e3a52] bg-[#0f2438]">
      {/* Toolbar de filtros */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[#1e3a52] p-3">
        <input
          type="text"
          placeholder="Buscar por TPA, matrícula, motivo, código SE…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setSkip(0);
          }}
          className="min-w-[260px] flex-1 rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[12px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
        />
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as StatusRemanejamentoUi | "TODOS");
            setSkip(0);
          }}
          className="rounded border border-[#2a5070] bg-[#0a1929] px-2 py-2 text-[12px] text-[#e8eef4]"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <Link
          href="/remanejamentos/novo"
          className="ml-auto rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a]"
        >
          + Novo Remanejamento
        </Link>
      </div>

      {/* Tabela */}
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-[#1e3a52] bg-[#0a1929] text-left text-[10px] font-bold uppercase tracking-wider text-[#94a8bd]">
              <th className="px-3 py-2">Data/Hora</th>
              <th className="px-3 py-2">Código SE</th>
              <th className="px-3 py-2">TPA Removido</th>
              <th className="px-3 py-2">Substituto</th>
              <th className="px-3 py-2">Faina · Função</th>
              <th className="px-3 py-2">Motivo</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Ação</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-[#94a8bd]">
                  Nenhum remanejamento encontrado com os filtros atuais.
                </td>
              </tr>
            ) : (
              pageItems.map((row) => {
                const r = row.item;
                const busy = busyIds.has(r.id);
                const canNotify = r.status === "APROVADO";
                const tpaNomeOut = row.tpaOut
                  ? row.tpaOut.nome
                  : "(nome removido)";
                const tpaMatOut = row.tpaOut?.matricula ?? "—";
                const tpaInNome = row.tpaIn
                  ? row.tpaIn.nome
                  : r.tpa_in_id
                    ? "(nome removido)"
                    : "—";
                const fainaLabel = row.faina
                  ? row.faina.nome
                  : "(faina removida)";
                const fainaCodigo = row.faina?.codigo ?? "—";
                const funcaoLabel = row.funcao
                  ? row.funcao.nome
                  : "(função removida)";
                const funcaoCodigo = row.funcao?.codigo ?? "—";
                return (
                  <tr
                    key={r.id}
                    className="border-b border-[#1e3a52] hover:bg-[#163554]/40"
                  >
                    <td className="px-3 py-2 font-mono text-[#d4a574]">
                      {new Date(r.created_at).toLocaleString("pt-BR")}
                    </td>
                    <td className="px-3 py-2 font-mono text-[#d4a574]">
                      <div>{r.codigo_se}</div>
                      <div className="font-mono text-[9px] text-[#5f7a92]">
                        {r.hash_evento.slice(0, 12)}…
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="font-semibold text-[#e8eef4]">
                        {tpaNomeOut}
                      </div>
                      <div className="font-mono text-[10px] text-[#94a8bd]">
                        {tpaMatOut}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-[#e8eef4]">{tpaInNome}</td>
                    <td className="px-3 py-2">
                      <div className="text-[#e8eef4]">{fainaLabel}</div>
                      <div className="font-mono text-[10px] text-[#94a8bd]">
                        {fainaCodigo}
                      </div>
                      <div className="text-[10px] text-[#94a8bd]">
                        {funcaoLabel} · <span className="font-mono">{funcaoCodigo}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-[#e8eef4]">{r.motivo}</td>
                    <td className="px-3 py-2">
                      <StatusBadge tone={toneForStatusRemanejamento(r.status)}>
                        {r.status}
                      </StatusBadge>
                    </td>
                    <td className="px-3 py-2">
                      {canNotify ? (
                        <button
                          type="button"
                          aria-label={`Notificar OGMO remanejamento ${r.codigo_se}`}
                          disabled={busy}
                          onClick={() => handleNotify(r.id)}
                          className="rounded bg-[#d4a574] px-3 py-1 text-[11px] font-bold text-[#0a1929] hover:bg-[#e8c49a] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {busy ? "Enviando…" : "Notificar OGMO"}
                        </button>
                      ) : (
                        <span className="text-[11px] text-[#5f7a92]">—</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Paginação + indicador */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#1e3a52] p-2 text-[10px] text-[#94a8bd]">
        <div className="font-mono">
          {total > 0
            ? `Mostrando ${pageStart + 1}–${pageEnd} de ${total}`
            : "Mostrando 0 de 0"}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={goPrev}
            disabled={skip === 0}
            className="rounded border border-[#2a5070] bg-[#0a1929] px-2 py-1 text-[11px] font-bold text-[#e8eef4] hover:border-[#d4a574] disabled:cursor-not-allowed disabled:opacity-50"
          >
            ← Anterior
          </button>
          <button
            type="button"
            onClick={goNext}
            disabled={skip + PAGE_LIMIT >= total}
            className="rounded border border-[#2a5070] bg-[#0a1929] px-2 py-1 text-[11px] font-bold text-[#e8eef4] hover:border-[#d4a574] disabled:cursor-not-allowed disabled:opacity-50"
          >
            Próximo →
          </button>
        </div>
      </div>
    </div>
  );
}
