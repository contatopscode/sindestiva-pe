"use client";

import { StatusBadge } from "@/app/_components/StatusBadge";
import type { AdminUser } from "@/lib/api";
import type { ReactNode } from "react";

function statusTone(status: AdminUser["status"]): "green" | "amber" | "red" | "muted" {
  if (status === "ATIVO") return "green";
  if (status === "INATIVO") return "muted";
  if (status === "BLOQUEADO") return "red";
  return "amber";
}

interface UsersTableProps {
  items: AdminUser[];
  busyId: string | null;
  onEdit: (user: AdminUser) => void;
  onToggleActive: (user: AdminUser) => void;
}

export function UsersTable({
  items,
  busyId,
  onEdit,
  onToggleActive,
}: UsersTableProps): ReactNode {
  if (items.length === 0) {
    return (
      <p className="rounded border border-[#1e3a52] bg-[#0d2137] px-4 py-8 text-center text-[13px] text-[#94a8bd]">
        Nenhum fiscal ou dirigente cadastrado.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-[#1e3a52]">
      <table className="min-w-full text-left text-[13px]">
        <thead className="bg-[#0d2137] text-[11px] uppercase tracking-wide text-[#5f7a92]">
          <tr>
            <th className="px-3 py-2">Nome</th>
            <th className="px-3 py-2">E-mail</th>
            <th className="px-3 py-2">Perfil</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Matrícula</th>
            <th className="px-3 py-2 text-right">Ações</th>
          </tr>
        </thead>
        <tbody>
          {items.map((user) => {
            const busy = busyId === user.id;
            const isActive = user.status === "ATIVO";
            return (
              <tr key={user.id} className="border-t border-[#1e3a52] hover:bg-[#122e47]/40">
                <td className="px-3 py-2 text-[#e8eef4]">{user.nome_completo ?? "—"}</td>
                <td className="px-3 py-2 text-[#94a8bd]">{user.email ?? "—"}</td>
                <td className="px-3 py-2">
                  <StatusBadge tone={user.role === "DIRIGENTE" ? "gold" : "cyan"}>
                    {user.role}
                  </StatusBadge>
                </td>
                <td className="px-3 py-2">
                  <StatusBadge tone={statusTone(user.status)}>{user.status}</StatusBadge>
                </td>
                <td className="px-3 py-2 text-[#94a8bd]">{user.matricula_sindicato ?? "—"}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      className="rounded border border-[#2a5070] px-2 py-1 text-[12px] text-[#94a8bd] hover:bg-[#163554] disabled:opacity-50"
                      onClick={() => onEdit(user)}
                      disabled={busy}
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      className={`rounded border px-2 py-1 text-[12px] disabled:opacity-50 ${
                        isActive
                          ? "border-[#e04a4a]/50 text-[#e04a4a] hover:bg-[#e04a4a]/10"
                          : "border-[#5dbb7d]/50 text-[#5dbb7d] hover:bg-[#5dbb7d]/10"
                      }`}
                      onClick={() => onToggleActive(user)}
                      disabled={busy}
                    >
                      {busy ? "…" : isActive ? "Desativar" : "Reativar"}
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
