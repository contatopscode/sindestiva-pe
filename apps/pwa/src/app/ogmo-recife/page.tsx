"use client";

import type { ReactNode } from "react";
import { OgmoRecifeEmbed } from "@sindestiva/ui";
import { PwaBottomNav } from "@/components/pwa-bottom-nav";

export default function OgmoRecifePwaPage(): ReactNode {
  return (
    <div className="phone-frame">
      <div className="phone-screen">
        <div className="phone-statusbar">
          <span>07:16</span>
          <span>📶 4G · 100%</span>
        </div>

        <div className="phone-body flex flex-col !overflow-hidden !p-0">
          <OgmoRecifeEmbed variant="pwa" />
        </div>

        <PwaBottomNav active="ogmo-recife" />
      </div>
    </div>
  );
}
