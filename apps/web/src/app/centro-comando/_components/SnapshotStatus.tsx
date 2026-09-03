// =============================================================================
// SINDESTIVA-PE · SnapshotStatus — badge do status do scrape
// Mostra status + timestamp + hash curto + botão "Atualizar".
// =============================================================================

"use client";

import type { ReactNode } from "react";
import { StatusBadge, toneForSnapshotStatus } from "@/app/_components/StatusBadge";
import { SNAPSHOT_STATUS_LABEL } from "@/lib/tipos";
import type { LousaSnapshotOut } from "@/lib/tipos";

export interface SnapshotStatusProps {
  snapshot: LousaSnapshotOut | null;
  onRefresh: () => void;
  loading: boolean;
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "—";
  }
}

function shortHash(h: string | null | undefined): string {
  if (!h) return "—";
  if (h === "0".repeat(64)) return "(mock)";
  return h.slice(0, 8);
}

export function SnapshotStatus({ snapshot, onRefresh, loading }: SnapshotStatusProps): ReactNode {
  const tone = toneForSnapshotStatus(snapshot?.status);
  const label = snapshot?.status ? SNAPSHOT_STATUS_LABEL[snapshot.status] : "Sem snapshot";

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-md border border-[#1e3a52] bg-[#0f2438] px-3 py-2">
      <StatusBadge tone={tone} pulse={snapshot?.status === "OK"}>
        ● {label}
      </StatusBadge>

      <span className="text-[11px] text-[#94a8bd]">
        Snapshot: <span className="font-mono text-[#e8eef4]">{shortHash(snapshot?.id)}</span>
      </span>

      <span className="text-[11px] text-[#94a8bd]">
        Scrape: <span className="font-mono text-[#e8eef4]">{formatTime(snapshot?.scraped_at)}</span>
      </span>

      <span className="text-[11px] text-[#94a8bd]">
        Hash: <span className="font-mono text-[#d4a574]">{shortHash(snapshot?.html_hash_sha256)}</span>
      </span>

      <button
        type="button"
        onClick={onRefresh}
        disabled={loading}
        className="ml-auto rounded border border-[#2a5070] px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-[#94a8bd] transition-colors hover:border-[#d4a574] hover:text-[#d4a574] disabled:opacity-50"
      >
        {loading ? "Atualizando…" : "↻ Atualizar"}
      </button>
    </div>
  );
}
