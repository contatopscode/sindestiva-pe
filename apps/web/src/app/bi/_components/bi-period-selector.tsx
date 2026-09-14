"use client";

import type { ReactNode } from "react";
import type { PeriodoDias } from "@/lib/tipos";
import { BI_PERIODOS } from "../bi-ui";

export function BiPeriodSelector({
  value,
  onChange,
}: {
  value: PeriodoDias;
  onChange: (p: PeriodoDias) => void;
}): ReactNode {
  return (
    <div
      className="flex gap-1 rounded-md border border-[#2a5070] bg-[#0f2438] p-1 text-xs"
      role="tablist"
      aria-label="Período do BI"
    >
      {BI_PERIODOS.map((p) => (
        <button
          key={p.value}
          type="button"
          role="tab"
          aria-selected={value === p.value}
          onClick={() => onChange(p.value)}
          className={`rounded px-3 py-1.5 transition ${
            value === p.value
              ? "bg-[#c8a04d] font-semibold text-[#0a1828]"
              : "text-[#94a8bd] hover:text-[#e8eef4]"
          }`}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}
