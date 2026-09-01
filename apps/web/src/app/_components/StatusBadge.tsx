// =============================================================================
// SINDESTIVA-PE · StatusBadge reutilizável
// Cores consistentes com a identidade visual portuário-industrial:
//   - OK / Presente / ACK  → verde
//   - Pendente / Parcial   → âmbar
//   - Erro / NACK / Ausente→ vermelho
//   - SENT / Info          → ciano
//   - Remanejado           → roxo
// =============================================================================

"use client";

import type { ReactNode } from "react";
import type { CellStatus, SnapshotStatus } from "@/lib/tipos";
import type { StatusOgmo } from "@sindestiva/shared";

export type BadgeTone = "green" | "amber" | "red" | "cyan" | "purple" | "gold" | "muted";

const TONE_CLS: Record<BadgeTone, string> = {
  green: "bg-[#5dbb7d]/15 text-[#5dbb7d] border-[#5dbb7d]/40",
  amber: "bg-[#e8a33d]/15 text-[#e8a33d] border-[#e8a33d]/40",
  red: "bg-[#e04a4a]/15 text-[#e04a4a] border-[#e04a4a]/40",
  cyan: "bg-[#4fb8c9]/15 text-[#4fb8c9] border-[#4fb8c9]/40",
  purple: "bg-[#9b7ec4]/15 text-[#9b7ec4] border-[#9b7ec4]/40",
  gold: "bg-[#d4a574]/15 text-[#d4a574] border-[#d4a574]/40",
  muted: "bg-[#1e3a52] text-[#94a8bd] border-[#2a5070]",
};

export function toneForCellStatus(s: CellStatus): BadgeTone {
  if (s === "AUSENTE") return "red";
  if (s === "REMANEJADO") return "amber";
  if (s === "CONFIRMADO") return "green";
  return "muted";
}

export function toneForSnapshotStatus(s: SnapshotStatus | null | undefined): BadgeTone {
  if (!s) return "muted";
  if (s === "OK") return "green";
  if (s === "PARCIAL") return "amber";
  if (s === "ERRO") return "red";
  if (s === "LAYOUT_MUDOU") return "purple";
  return "muted";
}

export function toneForOgmoStatus(s: StatusOgmo): BadgeTone {
  if (s === "ACK") return "green";
  if (s === "SENT") return "cyan";
  if (s === "PEND") return "amber";
  if (s === "NACK") return "red";
  return "muted";
}

export interface StatusBadgeProps {
  tone: BadgeTone;
  children: ReactNode;
  size?: "sm" | "md";
  pulse?: boolean;
  title?: string;
}

export function StatusBadge({ tone, children, size = "sm", pulse = false, title }: StatusBadgeProps): ReactNode {
  const sizeCls = size === "md" ? "px-2.5 py-1 text-[11px]" : "px-2 py-0.5 text-[10px]";
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded border font-bold uppercase tracking-wide ${sizeCls} ${TONE_CLS[tone]}`}
    >
      {pulse && (
        <span className={`inline-block h-1.5 w-1.5 rounded-full bg-current ${tone === "green" ? "animate-pulse" : ""}`} />
      )}
      {children}
    </span>
  );
}
