// =============================================================================
// SINDESTIVA-PE · /ogmo-recife — Portal OGMO Recife (FSW-2026-009)
// Distinto de /ogmo (fila WhatsApp). Embed + fallback em nova aba.
// =============================================================================

import type { ReactNode } from "react";
import { OgmoRecifeEmbed } from "@sindestiva/ui";

export const metadata = { title: "OGMO Recife · SINDESTIVA-PE" };

export default function OgmoRecifePage(): ReactNode {
  return (
    <div className="flex h-[calc(100vh-60px)] flex-col p-6">
      <OgmoRecifeEmbed variant="web" />
    </div>
  );
}
