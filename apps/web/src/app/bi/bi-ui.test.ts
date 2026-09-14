import { describe, expect, it } from "vitest";
import {
  BI_PERIODOS,
  formatCausaFaltaMotivo,
  periodoDiasFromTabValue,
  remanejamentosChartHeading,
  shouldUseBiFullPageEmptyState,
  topRemanejadosPeriodBadge,
} from "./bi-ui";

describe("BI período → periodo_dias", () => {
  it("mapeia as quatro tabs do protótipo para 7 / 30 / 90 / 365", () => {
    expect(BI_PERIODOS.map((p) => p.value)).toEqual([7, 30, 90, 365]);
    expect(BI_PERIODOS.map((p) => p.label)).toEqual([
      "7 dias",
      "30 dias",
      "3 meses",
      "12 meses",
    ]);
  });

  it("periodoDiasFromTabValue aceita apenas valores canônicos", () => {
    expect(periodoDiasFromTabValue(7)).toBe(7);
    expect(periodoDiasFromTabValue(30)).toBe(30);
    expect(periodoDiasFromTabValue(90)).toBe(90);
    expect(periodoDiasFromTabValue(365)).toBe(365);
    expect(periodoDiasFromTabValue(14)).toBeNull();
  });

  it("gera títulos e badges alinhados ao período", () => {
    expect(remanejamentosChartHeading(7)).toContain("7 DIAS");
    expect(remanejamentosChartHeading(90)).toContain("3 MESES");
    expect(topRemanejadosPeriodBadge(365)).toBe("12 MESES");
  });
});

describe("formatCausaFaltaMotivo", () => {
  it("normaliza ATESTADO_MEDICO para Atestado", () => {
    expect(formatCausaFaltaMotivo("ATESTADO_MEDICO")).toBe("Atestado");
  });
});

describe("layout vazio", () => {
  it("nunca usa EmptyState de página inteira quando total é zero", () => {
    expect(shouldUseBiFullPageEmptyState(0)).toBe(false);
    expect(shouldUseBiFullPageEmptyState(100)).toBe(false);
  });
});
