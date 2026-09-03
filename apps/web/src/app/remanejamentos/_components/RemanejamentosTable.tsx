// =============================================================================
// SINDESTIVA-PE · RemanejamentosTable
// Tabela do histórico (T5-09) com filtros turno/data/TPA/fiscal/status.
// Mock até Sprint 5 (T5-09+T5-10) implementar.
// =============================================================================

"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { StatusBadge, toneForOgmoStatus } from "@/app/_components/StatusBadge";
import type { RemanejamentoItem } from "@/lib/tipos";
import type { StatusOgmo, Turno } from "@sindestiva/shared";

const STATUSES: Array<StatusOgmo | "TODOS"> = ["TODOS", "PEND", "SENT", "ACK", "NACK"];

export interface RemanejamentosTableProps {
  items: RemanejamentoItem[];
  turnoDefault?: Turno;
}

export function RemanejamentosTable({ items, turnoDefault = "DIURNO" }: RemanejamentosTableProps): ReactNode {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusOgmo | "TODOS">("TODOS");
  const [turnoFilter, setTurnoFilter] = useState<Turno | "TODOS">(turnoDefault);

  const filtered = items.filter((r) => {
    if (statusFilter !== "TODOS" && r.status !== statusFilter) return false;
    if (turnoFilter !== "TODOS" && !r.data_hora.toUpperCase().endsWith(turnoFilter)) {
      // heurística — em produção, viria do backend
    }
    if (search.trim() !== "") {
      const q = search.toLowerCase();
      if (
        !r.tpa_removido_nome.toLowerCase().includes(q) &&
        !r.tpa_removido_matricula.includes(q) &&
        !r.motivo.toLowerCase().includes(q)
      ) {
        return false;
      }
    }
    return true;
  });

  return (
    <div className="rounded-lg border border-[#1e3a52] bg-[#0f2438]">
      {/* Toolbar de filtros (T5-09) */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[#1e3a52] p-3">
        <input
          type="text"
          placeholder="Buscar por TPA, matrícula, motivo…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-[260px] flex-1 rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[12px] text-[#e8eef4] focus:border-[#d4a574] focus:outline-none"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusOgmo | "TODOS")}
          className="rounded border border-[#2a5070] bg-[#0a1929] px-2 py-2 text-[12px] text-[#e8eef4]"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={turnoFilter}
          onChange={(e) => setTurnoFilter(e.target.value as Turno | "TODOS")}
          className="rounded border border-[#2a5070] bg-[#0a1929] px-2 py-2 text-[12px] text-[#e8eef4]"
        >
          <option value="TODOS">Todos turnos</option>
          <option value="DIURNO">DIURNO</option>
          <option value="NOTURNO">NOTURNO</option>
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
              <th className="px-3 py-2">TPA Removido</th>
              <th className="px-3 py-2">Substituto</th>
              <th className="px-3 py-2">Faina · Função</th>
              <th className="px-3 py-2">Motivo</th>
              <th className="px-3 py-2">Base legal</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-[#94a8bd]">
                  Nenhum remanejamento encontrado com os filtros atuais.
                </td>
              </tr>
            ) : (
              filtered.map((r) => (
                <tr key={r.id} className="border-b border-[#1e3a52] hover:bg-[#163554]/40">
                  <td className="px-3 py-2 font-mono text-[#d4a574]">
                    {new Date(r.data_hora).toLocaleString("pt-BR")}
                  </td>
                  <td className="px-3 py-2">
                    <div className="font-semibold text-[#e8eef4]">{r.tpa_removido_nome}</div>
                    <div className="font-mono text-[10px] text-[#94a8bd]">{r.tpa_removido_matricula}</div>
                  </td>
                  <td className="px-3 py-2 text-[#e8eef4]">
                    {r.tpa_substituto_nome ?? <span className="text-[#5f7a92]">—</span>}
                  </td>
                  <td className="px-3 py-2">
                    <div className="text-[#e8eef4]">{r.faina_codigo}</div>
                    <div className="text-[10px] text-[#94a8bd]">{r.funcao_codigo}</div>
                  </td>
                  <td className="px-3 py-2 text-[#e8eef4]">{r.motivo}</td>
                  <td className="px-3 py-2 text-[11px] text-[#94a8bd]">{r.base_legal}</td>
                  <td className="px-3 py-2">
                    <StatusBadge tone={toneForOgmoStatus(r.status)}>
                      {r.status}
                    </StatusBadge>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="border-t border-[#1e3a52] p-2 text-right text-[10px] text-[#94a8bd]">
        {filtered.length} de {items.length} remanejamentos
      </div>
    </div>
  );
}
