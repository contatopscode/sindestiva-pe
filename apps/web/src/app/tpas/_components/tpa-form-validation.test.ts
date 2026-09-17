import { describe, expect, it } from "vitest";
import { emptyTpaFormValues } from "./tpa-form-modal";
import { canSubmitTpaForm, tpaFormMissingFields } from "./tpa-form-validation";

describe("tpaFormMissingFields", () => {
  it("lista todos os campos obrigatórios vazios", () => {
    const missing = tpaFormMissingFields(emptyTpaFormValues());
    expect(missing.length).toBeGreaterThan(0);
    expect(missing.some((m) => m.includes("CPF"))).toBe(true);
    expect(missing.some((m) => m.includes("função"))).toBe(true);
  });

  it("canSubmit quando formulário completo", () => {
    const values = {
      ...emptyTpaFormValues(),
      cpf: "12345678901",
      nome_completo: "Tpa Teste",
      matricula_ogmo: "300443",
      telefone: "+5581999999999",
      funcao_ids: ["uuid-funcao"],
      funcao_base_id: "uuid-funcao",
    };
    expect(canSubmitTpaForm(values)).toBe(true);
    expect(tpaFormMissingFields(values)).toHaveLength(0);
  });
});
