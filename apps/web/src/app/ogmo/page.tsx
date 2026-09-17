// =============================================================================
// SINDESTIVA-PE · /ogmo — Painel da Fila OGMO
// =============================================================================

import type { ReactNode } from "react";
import { OgmoNotificacoesList } from "./_components/OgmoNotificacoesList";

export const metadata = { title: "Fila OGMO · SINDESTIVA-PE" };

export default function OgmoPage(): ReactNode {
  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Fila de Notificação OGMO</h1>
          <p className="section-subtitle">
            Acompanhe o status de cada remanejamento enviado ao OGMO/PE ·
            canal primário: WhatsApp (Evolution) · e-mail como fallback legado
          </p>
        </div>
      </div>

      <OgmoNotificacoesList />
    </div>
  );
}
