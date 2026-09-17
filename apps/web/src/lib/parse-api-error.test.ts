import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { parseApiError } from "./parse-api-error";

describe("parseApiError", () => {
  it("retorna mensagem de detail string", () => {
    expect(parseApiError(new ApiError(400, "CPF inválido"))).toBe("CPF inválido");
  });

  it("parseia objeto FastAPI { code, message }", () => {
    const detail = JSON.stringify({ code: "EMAIL_DUPLICATE", message: "E-mail já cadastrado." });
    expect(parseApiError(new ApiError(409, detail))).toBe("E-mail já cadastrado. (EMAIL_DUPLICATE)");
  });

  it("parseia array de erros de validação Pydantic", () => {
    const detail = JSON.stringify([
      { loc: ["body", "cpf"], msg: "String should have at least 11 characters" },
    ]);
    expect(parseApiError(new ApiError(422, detail))).toContain("body.cpf");
  });

  it("fallback para Error genérico", () => {
    expect(parseApiError(new Error("falha"))).toBe("falha");
  });
});
