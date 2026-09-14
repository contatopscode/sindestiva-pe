import { describe, expect, it } from "vitest";
import { labelPendenciaTpaOut } from "./remanejamento-modal-validation";

describe("labelPendenciaTpaOut", () => {
  it("mostra matrícula sem cadastro quando há matrícula e sem UUID", () => {
    expect(labelPendenciaTpaOut("162", "")).toBe("matrícula sem cadastro");
  });

  it("mantém TPA a remover quando matrícula vazia", () => {
    expect(labelPendenciaTpaOut("", "")).toBe("TPA a remover");
  });

  it("não acusa pendência de cadastro quando UUID resolvido", () => {
    expect(labelPendenciaTpaOut("162", "uuid-ok")).toBe("TPA a remover");
  });
});
