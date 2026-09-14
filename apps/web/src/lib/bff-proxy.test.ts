import { describe, expect, it } from "vitest";
import { BFF_PROXY_PREFIX, buildBffProxyUrl } from "./bff-proxy";

describe("buildBffProxyUrl", () => {
  it("prefixa path absoluto da API v1", () => {
    expect(
      buildBffProxyUrl("/api/v1/lousa/public/preview?porto=SUAPE&turno=DIURNO"),
    ).toBe(
      "/api/sindestiva/api/v1/lousa/public/preview?porto=SUAPE&turno=DIURNO",
    );
  });

  it("normaliza path sem barra inicial", () => {
    expect(buildBffProxyUrl("api/v1/bi/kpis")).toBe(
      "/api/sindestiva/api/v1/bi/kpis",
    );
  });

  it("usa prefixo público (não começa com _)", () => {
    expect(BFF_PROXY_PREFIX.startsWith("_")).toBe(false);
    expect(BFF_PROXY_PREFIX).toBe("/api/sindestiva");
  });
});
