import { describe, expect, it } from "vitest";
import {
  OGMO_RECIFE_DEFAULT_URL,
  ogmoRecifeEmbedTargets,
  resolveOgmoRecifeUrl,
} from "./ogmo-recife";

describe("resolveOgmoRecifeUrl", () => {
  it("usa default quando env ausente ou vazia", () => {
    expect(resolveOgmoRecifeUrl(undefined)).toBe(OGMO_RECIFE_DEFAULT_URL);
    expect(resolveOgmoRecifeUrl("")).toBe(OGMO_RECIFE_DEFAULT_URL);
    expect(resolveOgmoRecifeUrl("   ")).toBe(OGMO_RECIFE_DEFAULT_URL);
  });

  it("respeita NEXT_PUBLIC override trimado", () => {
    expect(resolveOgmoRecifeUrl("  https://custom.example/ogmo/  ")).toBe(
      "https://custom.example/ogmo/",
    );
  });
});

describe("ogmoRecifeEmbedTargets", () => {
  it("iframe src e fallback href coincidem", () => {
    const url = "http://www.ogmo-recife.org.br/ogmo/";
    const targets = ogmoRecifeEmbedTargets(url);
    expect(targets.iframeSrc).toBe(url);
    expect(targets.fallbackHref).toBe(url);
  });
});
