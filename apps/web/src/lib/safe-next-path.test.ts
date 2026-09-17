import { describe, expect, it } from "vitest";
import { DEFAULT_AFTER_LOGIN, sanitizeNextPath } from "./safe-next-path";

describe("sanitizeNextPath", () => {
  it("usa fallback quando ausente ou vazio", () => {
    expect(sanitizeNextPath(null)).toBe(DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath(undefined)).toBe(DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("")).toBe(DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("   ")).toBe(DEFAULT_AFTER_LOGIN);
  });

  it("aceita paths internos válidos", () => {
    expect(sanitizeNextPath("/centro-comando")).toBe("/centro-comando");
    expect(sanitizeNextPath("/remanejamentos?foo=1")).toBe("/remanejamentos?foo=1");
    expect(sanitizeNextPath("  /bi  ")).toBe("/bi");
  });

  it("rejeita open redirect", () => {
    expect(sanitizeNextPath("//evil.com")).toBe(DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("https://evil.com")).toBe(DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("/\\evil")).toBe(DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("javascript:alert(1)")).toBe(DEFAULT_AFTER_LOGIN);
    expect(sanitizeNextPath("/user@evil.com")).toBe(DEFAULT_AFTER_LOGIN);
  });
});
