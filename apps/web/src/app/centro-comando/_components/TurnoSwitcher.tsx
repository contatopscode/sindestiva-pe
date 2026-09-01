// =============================================================================
// SINDESTIVA-PE · TurnoSwitcher — alterna DIURNO (08-16) / NOTURNO (20-04)
// =============================================================================

"use client";

import type { ReactNode } from "react";
import type { Turno } from "@sindestiva/shared";

const TURNOS: Array<{ codigo: Turno; label: string }> = [
  { codigo: "DIURNO", label: "DIURNO" },
  { codigo: "NOTURNO", label: "NOTURNO" },
];

export interface TurnoSwitcherProps {
  value: Turno;
  onChange: (t: Turno) => void;
}

export function TurnoSwitcher({ value, onChange }: TurnoSwitcherProps): ReactNode {
  return (
    <div className="chip-group" role="tablist" aria-label="Turno">
      {TURNOS.map((t) => (
        <button
          key={t.codigo}
          type="button"
          role="tab"
          aria-selected={value === t.codigo}
          className={`chip ${value === t.codigo ? "active" : ""}`}
          onClick={() => onChange(t.codigo)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
