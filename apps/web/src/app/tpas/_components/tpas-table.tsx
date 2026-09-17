"use client";

import { StatusBadge } from "@/app/_components/StatusBadge";
import type { AdminTpa } from "@/lib/api";
import type { ReactNode } from "react";

function statusTone(status: AdminTpa["status_cadastro"]): "green" | "amber" | "red" | "muted" {
  if (status === "ATIVO") return "green";
  if (status === "AFASTADO") return "amber";
  if (status === "SUSPENSO") return "red";
  return "muted";
}

interface TpasTableProps {
  items: AdminTpa[];
  onEdit: (tpa: AdminTpa) => void;
}

export function TpasTable({ items, onEdit }: TpasTableProps): ReactNode {
  if (items.length === 0) {
    return (
      <p className="rounded border border-[#1e3a52] bg-[#0d2137] px-4 py-8 text-center text-[13px] text-[#94a8bd]">
        Nenhum TPA cadastrado.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-[#1e3a52]">
      <table className="min-w-full text-left text-[13px]">
        <thead className="bg-[#0d2137] text-[11px] uppercase tracking-wide text-[#5f7a92]">
          <tr>
            <th className="px-3 py-2">Nome</th>
            <th className="px-3 py-2">CPF</th>
            <th className="px-3 py-2">Matrícula OGMO</th>
            <th className="px-3 py-2">Função</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2 text-right">Ações</th>
          </tr>
        </thead>
        <tbody>
          {items.map((tpa) => (
            <tr key={tpa.id} className="border-t border-[#1e3a52] hover:bg-[#122e47]/40">
              <td className="px-3 py-2 text-[#e8eef4]">{tpa.nome_completo}</td>
              <td className="px-3 py-2 text-[#94a8bd]">{tpa.cpf}</td>
              <td className="px-3 py-2 text-[#94a8bd]">{tpa.matricula_ogmo}</td>
              <td className="px-3 py-2 text-[#94a8bd]">{tpa.funcao_nome}</td>
              <td className="px-3 py-2">
                <StatusBadge tone={statusTone(tpa.status_cadastro)}>
                  {tpa.status_cadastro}
                </StatusBadge>
              </td>
              <td className="px-3 py-2 text-right">
                <button
                  type="button"
                  className="rounded border border-[#2a5070] px-2 py-1 text-[12px] text-[#94a8bd] hover:bg-[#163554]"
                  onClick={() => onEdit(tpa)}
                >
                  Editar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
