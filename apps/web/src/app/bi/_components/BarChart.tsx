// =============================================================================
// SINDESTIVA-PE · /bi — Componente de gráfico de barras (ECharts)
// Wrapper leve do ECharts (client-only). Usado em /bi pra série temporal
// de remanejamentos. Drill-down (T7-06) é feito via onClick no gráfico.
// =============================================================================

"use client";

import { useEffect, useRef, type ReactNode } from "react";
import type { RemanejamentosPorDiaItem } from "@/lib/tipos";

export interface BarChartProps {
  items: RemanejamentosPorDiaItem[];
  /** Click handler: drill-down (T7-06). */
  onBarClick?: (data: RemanejamentosPorDiaItem) => void;
  /** Altura (px). Default 320. */
  height?: number;
}

export function BarChart({ items, onBarClick, height = 320 }: BarChartProps): ReactNode {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<unknown>(null);

  useEffect(() => {
    if (!ref.current) return;
    let disposed = false;

    // ECharts é client-only.
    void import("echarts").then((echarts) => {
      if (disposed || !ref.current) return;

      const dom = ref.current;
      const chart = echarts.init(dom);
      chartRef.current = chart;

      const datas = items.map((i) => i.data);
      const totais = items.map((i) => i.total);
      const maxV = Math.max(1, ...totais);

      chart.setOption({
        backgroundColor: "transparent",
        grid: { left: 40, right: 20, top: 30, bottom: 50 },
        tooltip: {
          trigger: "axis",
          backgroundColor: "#1a2540",
          borderColor: "#c8a04d",
          textStyle: { color: "#fff" },
          formatter: (params: unknown) => {
            const arr = params as Array<{ name: string; value: number }>;
            if (!arr[0]) return "";
            return `<strong>${arr[0].name}</strong><br/>${arr[0].value} remanejamento(s)`;
          },
        },
        xAxis: {
          type: "category",
          data: datas,
          axisLabel: { color: "#94a8bd", fontSize: 10, rotate: 45 },
          axisLine: { lineStyle: { color: "#2a5070" } },
        },
        yAxis: {
          type: "value",
          minInterval: 1,
          max: Math.ceil(maxV * 1.1),
          axisLabel: { color: "#94a8bd" },
          splitLine: { lineStyle: { color: "#1a2540" } },
        },
        series: [
          {
            type: "bar",
            data: totais,
            itemStyle: { color: "#c8a04d" },
            emphasis: { itemStyle: { color: "#fbbf24" } },
            barMaxWidth: 32,
          },
        ],
      });

      if (onBarClick) {
        chart.on("click", (params: unknown) => {
          const p = params as { dataIndex: number };
          const item = items[p.dataIndex];
          if (item) onBarClick(item);
        });
      }

      // Auto-resize.
      const handleResize = (): void => chart.resize();
      window.addEventListener("resize", handleResize);
      // Stash pra cleanup.
      (chart as unknown as { _handleResize?: () => void })._handleResize = handleResize;
    });

    return () => {
      disposed = true;
      const chart = chartRef.current as
        | (() => void)
        | { dispose: () => void; _handleResize?: () => void }
        | null;
      if (chart && typeof chart === "object" && "dispose" in chart) {
        if (chart._handleResize) window.removeEventListener("resize", chart._handleResize);
        chart.dispose();
      }
    };
  }, [items, onBarClick]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
