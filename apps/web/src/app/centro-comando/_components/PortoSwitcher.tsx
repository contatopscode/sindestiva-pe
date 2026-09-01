// =============================================================================
// SINDESTIVA-PE · PortoSwitcher — alterna SUAPE / RECIFE
// Chip-group estilo protótipo (SINDESTIVA-PE-PROTOTIPO.html, id="porto-switcher").
// =============================================================================

"use client";

import type { ReactNode } from "react";
import type { Porto } from "@sindestiva/shared";

const PORTOS: Porto[] = ["SUAPE", "RECIFE"];

export interface PortoSwitcherProps {
  value: Porto;
  onChange: (p: Porto) => void;
}

export function PortoSwitcher({ value, onChange }: PortoSwitcherProps): ReactNode {
  return (
    <div className="chip-group" role="tablist" aria-label="Porto">
      {PORTOS.map((p) => (
        <button
          key={p}
          type="button"
          role="tab"
          aria-selected={value === p}
          className={`chip ${value === p ? "active" : ""}`}
          onClick={() => onChange(p)}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
