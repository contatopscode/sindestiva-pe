import { describe, expect, it } from "vitest";
import {
  buildProxyResponseHeaders,
  proxyMethodOmitsBody,
  resolveUpstreamAuthorization,
} from "./bff-proxy-headers";
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

describe("buildProxyResponseHeaders", () => {
  it("remove content-encoding e content-length do upstream (body já decodificado)", () => {
    const upstream = new Headers({
      "content-type": "application/json",
      "content-encoding": "gzip",
      "content-length": "1234",
      "transfer-encoding": "chunked",
    });
    const out = buildProxyResponseHeaders(upstream, null);
    expect(out.get("content-type")).toBe("application/json");
    expect(out.has("content-encoding")).toBe(false);
    expect(out.has("content-length")).toBe(false);
    expect(out.has("transfer-encoding")).toBe(false);
    expect(out.has("access-control-allow-origin")).toBe(false);
  });

  it("define CORS só quando há Origin na request", () => {
    const upstream = new Headers({ "content-type": "application/json" });
    const out = buildProxyResponseHeaders(
      upstream,
      "https://web.hom.lousa.pscode.ia.br",
    );
    expect(out.get("access-control-allow-origin")).toBe(
      "https://web.hom.lousa.pscode.ia.br",
    );
  });
});

describe("proxyMethodOmitsBody", () => {
  it("omite body em GET e HEAD", () => {
    expect(proxyMethodOmitsBody("GET")).toBe(true);
    expect(proxyMethodOmitsBody("head")).toBe(true);
  });

  it("inclui body em POST, PATCH, PUT e DELETE", () => {
    expect(proxyMethodOmitsBody("POST")).toBe(false);
    expect(proxyMethodOmitsBody("patch")).toBe(false);
    expect(proxyMethodOmitsBody("PUT")).toBe(false);
    expect(proxyMethodOmitsBody("DELETE")).toBe(false);
  });
});

describe("resolveUpstreamAuthorization", () => {
  it("prefere Authorization do cliente", () => {
    expect(
      resolveUpstreamAuthorization("Bearer from-client", "cookie-jwt"),
    ).toBe("Bearer from-client");
  });

  it("usa cookie quando não há Authorization", () => {
    expect(resolveUpstreamAuthorization(null, "cookie-jwt")).toBe(
      "Bearer cookie-jwt",
    );
  });
});
