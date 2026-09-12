// =============================================================================
// SINDESTIVA-PE · PortoSwitcher — alterna SUAPE / RECIFE
// Chip-group estilo protótipo (SINDESTIVA-PE-PROTOTIPO.html, id="porto-switcher").
// =============================================================================

"use client";

import type { ReactNode } from "react";
import type { Porto } from "@sindestiva/shared";

const PORTOS: Array<{ codigo: Porto; label: string }> = [
  { codigo: "SUAPE", label: "Suape" },
  { codigo: "RECIFE", label: "Recife" },
];

export interface PortoSwitcherProps {
  value: Porto;
  onChange: (p: Porto) => void;
}

export function PortoSwitcher({ value, onChange }: PortoSwitcherProps): ReactNode {
  return (
    <div className="chip-group" role="tablist" aria-label="Porto">
      {PORTOS.map((p) => (
        <button
          key={p.codigo}
          type="button"
          role="tab"
          aria-selected={value === p.codigo}
          className={`chip ${value === p.codigo ? "active" : ""}`}
          onClick={() => onChange(p.codigo)}
          title={p.codigo}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}
