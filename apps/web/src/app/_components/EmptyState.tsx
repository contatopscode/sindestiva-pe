// =============================================================================
// SINDESTIVA-PE · EmptyState — exibido quando listas estão vazias.
// =============================================================================

import type { ReactNode } from "react";

export interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon = "📭", title, description, action }: EmptyStateProps): ReactNode {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-[#2a5070] bg-[#0f2438] px-6 py-12 text-center">
      <div className="text-4xl">{icon}</div>
      <div className="text-base font-semibold text-[#e8eef4]">{title}</div>
      {description && (
        <div className="max-w-md text-[13px] text-[#94a8bd]">{description}</div>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
