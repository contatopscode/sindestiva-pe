// =============================================================================
// SINDESTIVA-PE · LousaTable — réplica da lousa oficial do OGMO/PE
// Layout fiel ao protótipo (SINDESTIVA-PE-PROTOTIPO.html, função renderLousa
// linhas 2094-2174):
//   - 26 colunas agrupadas: Mando(6) | Terno(6) | Técnica(12) | Vigia(2)
//   - 11 linhas (fainas) ordenadas por `ordem`
//   - Header agrupado por categoria (colspan)
//   - Cada célula: matrícula + 1º nome + tooltip on hover/focus
//   - Click → callback para abrir modal de remanejamento
//
// Usa o CSS já existente em globals.css (lousa-table, ponteiro, faina-*, cat-*)
// para preservar 100% a identidade visual.
// =============================================================================

"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import type {
  LousaCellOut,
  Faina,
  Funcao,
  FuncaoCategoria,
} from "@/lib/tipos";
import { CAT_LABEL } from "@/lib/tipos";
import { CellTooltip } from "./CellTooltip";

export interface LousaTableProps {
  fainas: Faina[];
  funcoes: Funcao[];
  cells: LousaCellOut[];
  onCellClick?: (cell: LousaCellOut, funcao: Funcao, faina: Faina) => void;
}

const CATEGORIAS: FuncaoCategoria[] = ["MANDO", "TERNO", "TECNICA", "VIGIA"];

function classForCategoria(cat: FuncaoCategoria): string {
  switch (cat) {
    case "MANDO":   return "cat-mando";
    case "TERNO":   return "cat-terno";
    case "TECNICA": return "cat-tecnica";
    case "VIGIA":   return "cat-vigia";
  }
}

/** Cor da classe CSS por código de faina (mapeamento protótipo). */
function classForFaina(faina: Faina): string {
  // O protótipo usa sufixos fixos (producao, salario, etc.) baseados no nome.
  // Aqui derivamos do `cor_hex` do banco (que está no seed).
  const codigo = faina.codigo.toLowerCase();
  if (codigo.includes("producao"))   return "faina-producao";
  if (codigo.includes("salario"))    return "faina-salario";
  if (codigo.includes("sacaria"))    return "faina-sacaria";
  if (codigo.includes("ro-ro") || codigo.includes("veiculo")) return "faina-veiculo";
  if (codigo.includes("diversos"))   return "faina-diversos";
  if (codigo.includes("cadastro"))   return "faina-cadastro";
  if (codigo.includes("suplementar"))return "faina-suplementar";
  if (codigo.includes("altura"))     return "faina-altura";
  return "";
}

export function LousaTable({ fainas, funcoes, cells, onCellClick }: LousaTableProps): ReactNode {
  const [hover, setHover] = useState<{ cell: LousaCellOut; funcao: Funcao; faina: Faina; x: number; y: number } | null>(null);

  // Indexa cells por (faina_id, funcao_id) para lookup O(1).
  const cellIndex = useMemo(() => {
    const m = new Map<string, LousaCellOut>();
    for (const c of cells) m.set(`${c.faina_id}::${c.funcao_id}`, c);
    return m;
  }, [cells]);

  // Indexa fainas e funções por id.
  const fainasById = useMemo(() => {
    const m = new Map<string, Faina>();
    for (const f of fainas) m.set(f.id, f);
    return m;
  }, [fainas]);

  const funcoesById = useMemo(() => {
    const m = new Map<string, Funcao>();
    for (const fn of funcoes) m.set(fn.id, fn);
    return m;
  }, [funcoes]);

  // Agrupa funções por categoria preservando ordem.
  const funcoesPorCategoria = useMemo(() => {
    const out = new Map<FuncaoCategoria, Funcao[]>();
    for (const cat of CATEGORIAS) out.set(cat, []);
    for (const fn of funcoes) {
      const arr = out.get(fn.categoria);
      if (arr) arr.push(fn);
    }
    return out;
  }, [funcoes]);

  return (
    <div className="lousa-table-wrap">
      <table className="lousa-table" id="lousa-table" aria-label="Lousa portuária espelhada">
        <thead>
          {/* Linha 1: agrupamento por categoria (colspan) */}
          <tr>
            <th
              rowSpan={2}
              style={{ background: "var(--bg-raised)", minWidth: 120, textAlign: "left", paddingLeft: 10 }}
            >
              Faina
            </th>
            <th
              rowSpan={2}
              style={{ background: "var(--bg-raised)", minWidth: 50, color: "var(--accent-gold)" }}
              title="Ordem da faina no turno"
            >
              ⏱
            </th>
            {CATEGORIAS.map((cat) => {
              const arr = funcoesPorCategoria.get(cat) ?? [];
              if (arr.length === 0) return null;
              return (
                <th key={cat} colSpan={arr.length} className={classForCategoria(cat)}>
                  {CAT_LABEL[cat]}
                </th>
              );
            })}
          </tr>
          {/* Linha 2: cada função */}
          <tr>
            {CATEGORIAS.flatMap((cat) => (funcoesPorCategoria.get(cat) ?? []).map((fn) => (
              <th key={fn.id} title={fn.nome}>{fn.nome}</th>
            )))}
          </tr>
        </thead>
        <tbody>
          {fainas.map((f, idx) => (
            <tr key={f.id}>
              <th
                className={classForFaina(f)}
                style={{ color: f.cor_hex ?? undefined }}
              >
                {f.nome}
              </th>
              <th style={{ fontFamily: "monospace", fontSize: 9, color: "var(--accent-gold)" }}>
                T{idx + 1}
              </th>
              {funcoes.map((fn) => {
                const cell = cellIndex.get(`${f.id}::${fn.id}`);
                if (!cell) {
                  return <td key={fn.id} className="ponteiro vazio">·</td>;
                }
                const cls = ["ponteiro"];
                if (cell.status === "AUSENTE") cls.push("ausente");
                else if (cell.status === "REMANEJADO") cls.push("remanejado");
                else if (cell.status === "CONFIRMADO") cls.push("confirmado");
                if (!cell.tpa_id) cls.push("vazio");
                const isEmpty = !cell.tpa_id;

                return (
                  <td
                    key={fn.id}
                    className={cls.join(" ")}
                    tabIndex={isEmpty ? -1 : 0}
                    role="gridcell"
                    aria-label={
                      isEmpty
                        ? `${f.nome} · ${fn.nome} · vazio`
                        : `${f.nome} · ${fn.nome} · ${cell.tpa_nome ?? "?"} (${cell.tpa_matricula})`
                    }
                    onMouseEnter={(e) =>
                      setHover({ cell, funcao: fn, faina: f, x: e.clientX, y: e.clientY })
                    }
                    onMouseMove={(e) =>
                      setHover((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : null))
                    }
                    onMouseLeave={() => setHover(null)}
                    onFocus={(e) => {
                      const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
                      setHover({ cell, funcao: fn, faina: f, x: r.left + r.width / 2, y: r.bottom });
                    }}
                    onBlur={() => setHover(null)}
                    onClick={() => onCellClick?.(cell, fn, f)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onCellClick?.(cell, fn, f);
                      }
                    }}
                  >
                    {cell.tpa_matricula ? (
                      <>
                        {cell.tpa_matricula}
                        <span className="tpa-nome">{cell.tpa_nome?.split(" ")[0] ?? ""}</span>
                      </>
                    ) : (
                      "·"
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {hover && (
        <div
          style={{
            position: "fixed",
            top: hover.y + 12,
            left: Math.min(hover.x + 12, (typeof window !== "undefined" ? window.innerWidth : 1200) - 280),
          }}
        >
          <CellTooltip cell={hover.cell} funcao={hover.funcao} faina={hover.faina} />
        </div>
      )}
    </div>
  );
}
