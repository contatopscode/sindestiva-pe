import { describe, expect, it } from "vitest";
import {
  AUTH_COOKIE_NAME,
  buildAuthSetCookieHeader,
  buildLegacySharedClearCookieHeader,
  buildLoginSetCookieHeaders,
  resolveAuthCookieDomain,
} from "./auth-cookie";

describe("resolveAuthCookieDomain", () => {
  it("localhost é host-only (sem Domain)", () => {
    expect(resolveAuthCookieDomain("localhost:3010")).toBeUndefined();
  });

  it("HOM usa .hom.lousa.pscode.ia.br, não .pscode.ia.br", () => {
    expect(resolveAuthCookieDomain("web.hom.lousa.pscode.ia.br")).toBe(
      ".hom.lousa.pscode.ia.br",
    );
    expect(resolveAuthCookieDomain("web.hom.lousa.pscode.ia.br")).not.toBe(
      ".pscode.ia.br",
    );
  });

  it("prod lousa mantém Domain=.pscode.ia.br", () => {
    expect(resolveAuthCookieDomain("web.lousa.pscode.ia.br")).toBe(
      ".pscode.ia.br",
    );
  });
});

describe("buildAuthSetCookieHeader", () => {
  it("HOM não inclui Domain=.pscode.ia.br no cookie de sessão", () => {
    const header = buildAuthSetCookieHeader("jwt-test", "web.hom.lousa.pscode.ia.br");
    expect(header).toContain(`${AUTH_COOKIE_NAME}=jwt-test`);
    expect(header).toContain("Domain=.hom.lousa.pscode.ia.br");
    expect(header).not.toContain("Domain=.pscode.ia.br");
  });

  it("prod inclui Domain=.pscode.ia.br", () => {
    const header = buildAuthSetCookieHeader("jwt-test", "web.lousa.pscode.ia.br");
    expect(header).toContain("Domain=.pscode.ia.br");
  });
});

describe("buildLoginSetCookieHeaders", () => {
  it("HOM login envia clear do legado .pscode.ia.br", () => {
    const headers = buildLoginSetCookieHeaders("jwt", "web.hom.lousa.pscode.ia.br");
    expect(headers.length).toBeGreaterThanOrEqual(2);
    const legacyClear = headers.find((h) =>
      h.includes("Domain=.pscode.ia.br") && h.includes("Max-Age=0"),
    );
    expect(legacyClear).toBeDefined();
    expect(buildLegacySharedClearCookieHeader()).toContain("Domain=.pscode.ia.br");
  });
});
